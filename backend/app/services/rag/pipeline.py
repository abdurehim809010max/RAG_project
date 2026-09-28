"""
backend/app/services/rag/pipeline.py

Orchestrator: Query -> Retrieval -> LLM generation.

Ties retriever.py (finds relevant chunks) together with a call to Gemini
(generates the actual answer grounded in those chunks).

Setup:
    pip install google-genai python-dotenv
    Add GEMINI_API_KEY=your-key-here to your .env file.

Failure handling
----------------
Gemini regularly returns 503 ("high demand") and model names get retired,
so generation is wrapped in a bounded retry/fallback loop:

  * The primary model gets `primary_attempts` tries, with a short pause
    between them (only for transient errors: 429/500/502/503/504 and
    network drops).
  * Each fallback model gets one try, no pause.
  * A 404 (model name doesn't exist / was retired) skips to the next model
    immediately — a wrong fallback name costs nothing.
  * 401/403 (bad key or permissions) stops at once: no model will fix that.
  * If nothing works, an exception is raised. It is NEVER returned as if it
    were an answer, so the API can report a real error status.
"""

import logging
import os
import time

import httpx
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import APIError

load_dotenv()

from .retriever import Retriever

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-3.8-flash"

# Tried in order after the primary model. Names that don't exist are skipped
# instantly (404), so stale entries are harmless — but prune them when you
# notice them in the logs.
FALLBACK_MODELS = [
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
]

_TRANSIENT_CODES = {429, 500, 502, 503, 504}
_AUTH_CODES = {401, 403}

SYSTEM_PROMPT = (
    "አንተ የኢትዮጵያ ፌዴራል ጠቅላይ ፍርድ ቤት ሰበር ሰሚ ችሎት ውሳኔዎችን መሠረት አድርገህ ጥያቄዎችን "
    "የምትመልስ ረዳት ነህ። ከዚህ በታች የቀረቡልህን የፍርድ ውሳኔ ክፍሎች (context) ብቻ ተጠቅመህ "
    "መልስ። በተሰጠው መረጃ ውስጥ መልስ ከሌለ፣ 'በተሰጠው መረጃ ውስጥ ይህን ጥያቄ የሚመልስ በቂ መረጃ "
    "አላገኘሁም' በማለት ንገረኝ እንጂ ራስህ ገምተህ አትመልስ።"
)


class LLMUnavailableError(Exception):
    """Gemini couldn't produce an answer right now (overloaded, network
    down, every model failed). Safe for the client to retry later."""


class LLMConfigError(Exception):
    """Gemini rejected our credentials/permissions. Retrying won't help —
    the server's configuration needs fixing."""


def build_prompt(query: str, chunks: list[dict]) -> str:
    context_blocks = []
    for c in chunks:
        context_blocks.append(
            f"[መዝገብ ቁጥር {c['case_number']}, {c['page_range']}]\n{c['text']}"
        )
    context = "\n\n---\n\n".join(context_blocks)

    return (
        f"{SYSTEM_PROMPT}\n\n"
        f"### አውድ (Context)\n{context}\n\n"
        f"### ጥያቄ (Question)\n{query}\n\n"
        f"### መልስ (Answer)"
    )


def _finish_reason(response) -> str:
    try:
        return str(response.candidates[0].finish_reason)
    except (AttributeError, IndexError, TypeError):
        return "no candidates"


class RagPipeline:
    def __init__(self, retriever: Retriever, model_name: str = DEFAULT_MODEL,
                 api_key: str | None = None,
                 fallback_models: list[str] | None = None,
                 primary_attempts: int = 2,
                 retry_delay: float = 2.0):
        self.retriever = retriever
        self.model_name = model_name
        self.fallback_models = FALLBACK_MODELS if fallback_models is None else fallback_models
        self.primary_attempts = primary_attempts
        self.retry_delay = retry_delay
        self._client = genai.Client(api_key=api_key or os.environ["GEMINI_API_KEY"])

    def _generate_with_retry(self, prompt: str) -> str:
        """Return Gemini's answer text, or raise LLMUnavailableError /
        LLMConfigError. Never returns an error message as an answer."""
        models = [self.model_name] + [m for m in self.fallback_models if m != self.model_name]
        config = types.GenerateContentConfig(
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
        )
        last_problem = "no attempt made"

        for model in models:
            attempts = self.primary_attempts if model == self.model_name else 1

            for attempt in range(1, attempts + 1):
                try:
                    response = self._client.models.generate_content(
                        model=model, contents=prompt, config=config,
                    )
                except APIError as e:
                    if e.code in _AUTH_CODES:
                        raise LLMConfigError(
                            f"Gemini rejected the API key/permissions (HTTP {e.code})"
                        ) from e

                    last_problem = f"{model}: HTTP {e.code}"
                    if e.code == 404:
                        logger.warning(
                            "Gemini model '%s' not found (404) - skipping it.", model)
                        break
                    if e.code in _TRANSIENT_CODES:
                        logger.warning("Model '%s' returned %s (try %d/%d).",
                                       model, e.code, attempt, attempts)
                        if attempt < attempts:
                            time.sleep(self.retry_delay)
                        continue
                    logger.warning("Model '%s' rejected the request (HTTP %s) - "
                                   "trying the next model.", model, e.code)
                    break
                except httpx.TransportError as e:
                    last_problem = f"{model}: network error ({type(e).__name__})"
                    logger.warning("Network error calling '%s': %s (try %d/%d).",
                                   model, type(e).__name__, attempt, attempts)
                    if attempt < attempts:
                        time.sleep(self.retry_delay)
                    continue

                text = (response.text or "").strip()
                if text:
                    if model != self.model_name:
                        logger.warning("Answered by fallback model '%s' (primary '%s' was unavailable).",
                                       model, self.model_name)
                    return text

                last_problem = f"{model}: empty response ({_finish_reason(response)})"
                logger.warning("Model '%s' returned no text (%s) - trying the next model.",
                               model, _finish_reason(response))
                break

        raise LLMUnavailableError(f"All Gemini models failed. Last problem: {last_problem}")

    def answer(self, query: str, top_k: int = 5,
               case_number: str | None = None,
               volume: int | None = None,
               legal_category: str | None = None,
               auto_filter_case_number: bool = True) -> dict:
        """
        Run the full pipeline for one query: retrieve relevant chunks, ask
        Gemini to answer using only those chunks, and return the answer plus
        the sources it was grounded in (what CitationCard.jsx will render).

        case_number / volume: pass these when the caller already knows which
        case the question is about; otherwise the retriever reads the
        "በቅጽ N፣ መዝገብ ቁጥር N" prefix from the question.

        Raises LLMUnavailableError / LLMConfigError if generation fails.
        """
        chunks = self.retriever.retrieve(
            query, top_k=top_k,
            case_number=case_number, volume=volume,
            legal_category=legal_category,
            auto_filter_case_number=auto_filter_case_number,
        )

        if not chunks:
            return {
                "answer": "ተዛማጅ የፍርድ ውሳኔ አላገኘሁም።",
                "sources": [],
            }

        answer_text = self._generate_with_retry(build_prompt(query, chunks))

        return {
            "answer": answer_text,
            "sources": [
                {
                    "case_number": c["case_number"],
                    "page_range": c["page_range"],
                    "legal_category": c["legal_category"],
                    "chunk_id": c["chunk_id"],
                    "distance": c["distance"],
                }
                for c in chunks
            ],
        }
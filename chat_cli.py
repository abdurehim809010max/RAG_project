"""
chat_cli.py

Terminal chat client for the RAG API. It talks to the running server over
HTTP — it does not import any backend code — so it behaves exactly like the
future React frontend will.

Start the server first (in another terminal, from the project root):
    uvicorn backend.app.main:app --reload

Then:
    python chat_cli.py

Start each question with the volume and case number:
    በቅጽ 15፣ መዝገብ ቁጥር 80343 በውሳኔው ውስጥ የተገለጸ ዋና የሕግ መርህ ምን ነበር?
Type 'exit' to quit.
"""

import argparse
import sys
import time
from collections import OrderedDict

import httpx

DEFAULT_URL = "http://127.0.0.1:8000"
CHAT_PATH = "/api/v1/chat"
MAX_BUSY_TRIES = 3          # total tries when the server answers 503
DEFAULT_RETRY_WAIT = 10     # used if the server sends no Retry-After
MAX_RETRY_WAIT = 30         # never wait longer than this between tries

START_HINT = "Start it with:  uvicorn backend.app.main:app --reload"


def format_sources(sources: list[dict]) -> str:
    """One line per case (not per chunk): the API returns several chunks
    from the same case, which would otherwise print as repeated lines."""
    grouped: "OrderedDict[tuple, int]" = OrderedDict()
    for s in sources:
        key = (s["case_number"], s["legal_category"], s["page_range"])
        grouped[key] = grouped.get(key, 0) + 1

    lines = []
    for (case_number, category, pages), n in grouped.items():
        lines.append(f"  • መዝገብ ቁጥር {case_number} | {category} | {pages}  ({n} ክፍሎች)")
    return "\n".join(lines)


def _detail(response: httpx.Response) -> str:
    """Pull a readable message out of an error response."""
    try:
        detail = response.json().get("detail")
    except ValueError:
        return response.text[:200] or f"HTTP {response.status_code}"
    if isinstance(detail, list) and detail:      # FastAPI validation errors
        return str(detail[0].get("msg", detail[0]))
    return str(detail)


def _retry_wait(response: httpx.Response) -> int:
    try:
        wait = int(response.headers.get("retry-after", DEFAULT_RETRY_WAIT))
    except ValueError:
        wait = DEFAULT_RETRY_WAIT
    return max(1, min(wait, MAX_RETRY_WAIT))


def ask(client: httpx.Client, question: str, top_k: int | None = None,
        sleep=time.sleep) -> tuple[dict | None, str | None]:
    """Send one question. Returns (response_json, None) on success or
    (None, error_message) on failure. A 503 (Gemini busy) is retried after
    the server's Retry-After delay."""
    payload: dict = {"question": question}
    if top_k:
        payload["top_k"] = top_k

    for attempt in range(1, MAX_BUSY_TRIES + 1):
        try:
            response = client.post(CHAT_PATH, json=payload)
        except httpx.ConnectError:
            return None, f"Cannot reach the server at {client.base_url}. {START_HINT}"
        except httpx.TimeoutException:
            return None, "The server took too long to answer. Try again in a moment."

        if response.status_code == 200:
            return response.json(), None

        if response.status_code == 503 and attempt < MAX_BUSY_TRIES:
            wait = _retry_wait(response)
            print(f"  (service busy - retrying in {wait}s, try {attempt + 1}/{MAX_BUSY_TRIES})")
            sleep(wait)
            continue

        return None, _detail(response)

    return None, "Service is busy. Please try again later."   # not reached; safety net


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", default=DEFAULT_URL, help="API base URL")
    parser.add_argument("--top-k", type=int, default=None,
                        help="How many chunks to retrieve (server default if omitted)")
    args = parser.parse_args()

    client = httpx.Client(base_url=args.url, timeout=httpx.Timeout(120.0, connect=5.0))

    # Fail early and clearly if the server isn't up.
    try:
        client.get("/openapi.json", timeout=5.0)
    except httpx.HTTPError:
        print(f"Cannot reach the API at {args.url}.\n{START_HINT}")
        sys.exit(1)

    print("Ethiopian Cassation RAG — terminal chat")
    print("Start your question with:  በቅጽ 15፣ መዝገብ ቁጥር <number>")
    print("Type 'exit' to quit.\n")

    while True:
        try:
            question = input("ጥያቄዎን ያስገቡ: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not question or question.lower() in ("exit", "quit", "q"):
            break

        data, error = ask(client, question, top_k=args.top_k)

        if error:
            print(f"\n[!] {error}\n")
            continue

        print(f"\nመልስ:\n{data['answer']}\n")
        if data["sources"]:
            print("ምንጮች:")
            print(format_sources(data["sources"]))
        print()


if __name__ == "__main__":
    main()

# syntax=docker/dockerfile:1
FROM python:3.14-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /build

COPY backend/requirements.txt ./requirements.txt

# The cache mount keeps downloaded wheels even if the build fails or is cancelled.
# Torch is installed first from the CPU-only index so pip can't pick the multi-GB CUDA build.
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m venv "$VIRTUAL_ENV" \
    && pip install --upgrade pip \
    && (iconv -f UTF-16 -t UTF-8 requirements.txt > /tmp/requirements.txt \
        || cp requirements.txt /tmp/requirements.txt) \
    && grep -viE '^(pywin32|pywinpty|win32_setctime|torch==|pytest|ruff)' /tmp/requirements.txt > /tmp/requirements.clean.txt \
    && pip install --retries 10 --timeout 60 torch==2.14.0 --index-url https://download.pytorch.org/whl/cpu \
    && pip install --retries 10 --timeout 60 --requirement /tmp/requirements.clean.txt \
    && rm /tmp/requirements*.txt


FROM python:3.14-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    HF_HOME=/app/backend/data/hf_cache

WORKDIR /app

# Your network redirects plain-HTTP apt traffic, so switch Debian to HTTPS.
RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 appuser

COPY --from=builder /opt/venv /opt/venv
COPY backend/app ./backend/app

RUN mkdir -p /app/backend/data/vector_db /app/backend/data/hf_cache \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health')"

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
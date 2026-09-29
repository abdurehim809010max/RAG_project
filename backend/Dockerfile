FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN iconv -f UTF-16 -t UTF-8 requirements.txt > /tmp/requirements.txt \
    && pip install --requirement /tmp/requirements.txt \
    && rm /tmp/requirements.txt

COPY backend/app ./backend/app

EXPOSE 8000
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]

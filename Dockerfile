# ═══════════════════════════════════════════════════════════════════════════════
# Stage 1 — Builder
# Cache-bust: 2026-06-23-port-fix-v2
# ═══════════════════════════════════════════════════════════════════════════════
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt

# ═══════════════════════════════════════════════════════════════════════════════
# Stage 2 — Runtime
# ═══════════════════════════════════════════════════════════════════════════════
FROM python:3.11-slim AS runtime

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
COPY . .

RUN useradd -m -u 1001 kumip && \
    mkdir -p /app/data/processed /app/models/saved /app/logs && \
    chown -R kumip:kumip /app

USER kumip

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

CMD ["sh", "-c", "test -f data/processed/route_profiles.csv || python scripts/generate_data.py; echo '>>> STARTING UVICORN ON PORT:' ${PORT:-8000}; exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]

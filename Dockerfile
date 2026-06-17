# ═══════════════════════════════════════════════════════════════════════════════
# Stage 1 — Builder: install deps into a clean layer
# ═══════════════════════════════════════════════════════════════════════════════
FROM python:3.11-slim AS builder

WORKDIR /app

# System deps for geospatial + Prophet
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libgdal-dev libproj-dev libgeos-dev libspatialindex-dev \
    libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt

# ═══════════════════════════════════════════════════════════════════════════════
# Stage 2 — Runtime: lean final image
# ═══════════════════════════════════════════════════════════════════════════════
FROM python:3.11-slim AS runtime

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgeos-dev libproj-dev libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY . .

# Create non-root user
RUN useradd -m -u 1001 kumip && \
    mkdir -p /app/data/processed /app/models/saved /app/logs && \
    chown -R kumip:kumip /app

USER kumip

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]

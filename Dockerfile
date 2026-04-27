FROM python:3.12-slim AS base

# ── System dependencies ───────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# ── Non-root user ─────────────────────────────────────────────────────────────
RUN addgroup --system app && adduser --system --ingroup app app

WORKDIR /app

# ── Python dependencies (own layer for caching) ───────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ── Application source ────────────────────────────────────────────────────────
COPY --chown=app:app . .

# ── Runtime ───────────────────────────────────────────────────────────────────
USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD curl -f http://localhost:8000/health || exit 1

# Use $PORT env-var so the image works on cloud platforms (Railway, Render, etc.)
# Fall back to 8000 if unset.
CMD ["sh", "-c", \
     "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]

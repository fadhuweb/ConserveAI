# ConserveAI backend — FastAPI on Fly.io.
# Uses the slim runtime requirements (no torch/xgboost/shap) and bundles the
# production model. GEE credentials, DB URL, etc. are injected as Fly secrets.
FROM python:3.12-slim

# psycopg2 + scientific wheels need a couple of build/runtime libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    ENVIRONMENT=production

WORKDIR /app

# Install deps first for better layer caching
COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

# App code + the production model (.dockerignore keeps the image lean)
COPY src/ ./src/
COPY results/production/ ./results/production/

EXPOSE 8000

# Fly sets $PORT; default to 8000 locally
CMD ["sh", "-c", "uvicorn src.backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

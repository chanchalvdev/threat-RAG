# ---------- build stage ----------
FROM python:3.13-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ---------- runtime stage ----------
FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/install/bin:$PATH" \
    PYTHONPATH="/app"

WORKDIR /app

# Non-root user
RUN addgroup --system app && adduser --system --ingroup app app

COPY --from=builder /install /install
COPY app/ ./app/

RUN chown -R app:app /app
USER app

EXPOSE 8000

# Cloud Run/Render inject $PORT; default to 8000 locally
# Behind a hosting proxy, --proxy-headers makes rate limits see the visitor's address instead of the
# proxy's. Set FORWARDED_ALLOW_IPS to the proxy's address (uvicorn reads it); the default trusts none.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers"]

# ==========================================
# Stage 1: Builder
# ==========================================
FROM python:3.12-slim-bookworm AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    python3-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    libjpeg-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:/root/.local/bin:$PATH"

COPY pyproject.toml uv.lock ./
COPY src/ ./src/
COPY README.md LICENSE ./

RUN uv venv /app/.venv && \
    . /app/.venv/bin/activate && \
    uv sync --frozen --no-dev

RUN . /app/.venv/bin/activate && \
    uv pip install -e .

# ==========================================
# Stage 2: Runtime
# ==========================================
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    PPTX_OUTPUT_ROOT=/output

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2 \
    libxslt1.1 \
    libjpeg62-turbo \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r pptxuser && \
    useradd -r -g pptxuser -u 1000 pptxuser && \
    mkdir -p /output /app && \
    chown -R pptxuser:pptxuser /output /app

COPY --from=builder --chown=pptxuser:pptxuser /app/.venv /app/.venv
COPY --from=builder --chown=pptxuser:pptxuser /app/src /app/src
COPY --from=builder --chown=pptxuser:pptxuser /app/pyproject.toml /app/
COPY --chown=pptxuser:pptxuser templates/ /app/templates/
COPY --chown=pptxuser:pptxuser samples/ /app/samples/

USER pptxuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["gunicorn", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "1", \
     "--worker-class", "sync", \
     "--timeout", "300", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info", \
     "pptx_generator.api.flask_app:app"]

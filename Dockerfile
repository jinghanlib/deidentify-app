# ── Stage 1: Build & download models ──
FROM python:3.11-slim AS builder

WORKDIR /build
COPY requirements.txt .

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /venv \
    && /venv/bin/pip install --no-cache-dir -r requirements.txt \
    && /venv/bin/python -m spacy download en_core_web_lg

# ── Stage 2: Production image ──
FROM python:3.11-slim

# Image metadata
LABEL maintainer="your-lab@university.edu"
LABEL description="Local-only PII de-identification tool for human subjects research"
LABEL version="1.0.0"
LABEL org.opencontainers.image.title="De-Identification App"
LABEL org.opencontainers.image.description="HIPAA-compliant PII removal for research data"
LABEL org.opencontainers.image.version="1.0.0"

# Security: run as non-root user
RUN groupadd -r appuser && useradd -r -g appuser -d /home/appuser -s /sbin/nologin appuser

WORKDIR /app

# Copy virtualenv from builder
COPY --from=builder /venv /venv
ENV PATH="/venv/bin:$PATH"

# Copy application code
COPY app/ ./app/
COPY data/sample/ ./data/sample/

# Create directories for runtime data and output
RUN mkdir -p /workspace/data /workspace/output /workspace/audit \
    && chown -R appuser:appuser /app /workspace

# Switch to non-root user
USER appuser

# Streamlit configuration: disable telemetry, set port
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_THEME_BASE=light

EXPOSE 8501

# Note: Healthcheck is intentionally omitted because this container runs with
# --network none for security. The healthcheck would fail without network access.
# If you need health monitoring, run without network isolation or use a
# file-based health indicator.

ENTRYPOINT ["streamlit", "run", "app/main.py", "--server.fileWatcherType=none"]

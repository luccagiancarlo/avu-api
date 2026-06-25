# syntax=docker/dockerfile:1.7

# =====================================================================
# Base — debian slim com Python 3.11 (ibm-db tem wheels pré-compilados
# para Linux x86_64; em ARM/Mac o build local roda via docker buildx).
# =====================================================================
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    IBM_DB_HOME=/opt/ibm_db

# libxml2 e libssl são necessários pelo driver DB2; build-essential só
# entra no estágio builder.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libxml2 \
        libssl3 \
        ca-certificates \
        curl \
    && rm -rf /var/lib/apt/lists/*

# =====================================================================
# Builder — instala deps Python em um venv que copiamos para a imagem final
# =====================================================================
FROM base AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml ./
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip && \
    /opt/venv/bin/pip install .

# =====================================================================
# Runtime
# =====================================================================
FROM base AS runtime

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY app ./app
COPY alembic.ini ./alembic.ini
COPY alembic ./alembic

# Usuário não-root
RUN useradd -m -u 1000 avu && \
    mkdir -p /secrets && chown -R avu:avu /app /secrets
USER avu

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

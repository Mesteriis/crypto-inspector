# Home Assistant Add-on: Crypto Inspect
# https://developers.home-assistant.io/docs/add-ons
# syntax=docker/dockerfile:1.4

# =============================================================================
# Stage 1: Builder - Install dependencies and build wheels
# =============================================================================
ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base-debian:bookworm
FROM ${BUILD_FROM} AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gfortran \
    pkg-config \
    libopenblas-dev \
    python3-dev \
    python3-venv \
    curl \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install uv package manager
ENV UV_INSTALL_DIR="/opt/uv" \
    UV_NO_PROGRESS=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && ln -s /opt/uv/uv /usr/local/bin/uv

WORKDIR /app

# Copy only dependency files first (better layer caching)
COPY pyproject.toml uv.lock ./

# Install dependencies system-wide (no venv)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system --python $(which python3) -r pyproject.toml

# =============================================================================
# Stage 2: Runtime - Minimal production image
# =============================================================================
ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base-debian:bookworm
FROM ${BUILD_FROM} AS runtime

# Labels
LABEL maintainer="Crypto Inspect" \
    org.opencontainers.image.title="Crypto Inspect" \
    org.opencontainers.image.description="Cryptocurrency data collector for Home Assistant"

# Install only runtime dependencies (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-venv \
    postgresql-client \
    libopenblas0 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && rm -rf /tmp/* /var/tmp/* \
    && find /var/log -type f -delete

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random

WORKDIR /app

# Copy application code
COPY --chown=root:root src ./src
COPY --chown=root:root alembic ./alembic
COPY --chown=root:root alembic.ini ./

# Copy rootfs (s6-overlay service scripts)
COPY rootfs /

# Set permissions for s6-overlay scripts
RUN find /etc/s6-overlay -type f -exec chmod 755 {} + 2>/dev/null || true \
    && find /etc/cont-init.d -type f -exec chmod 755 {} + 2>/dev/null || true \
    && find /etc/services.d -type f -name "run" -exec chmod 755 {} + 2>/dev/null || true \
    && find /etc/services.d -type f -name "finish" -exec chmod 755 {} + 2>/dev/null || true

# Create data directory for SQLite
RUN mkdir -p /data && chmod 755 /data

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1
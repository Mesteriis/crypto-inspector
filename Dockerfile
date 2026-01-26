# Home Assistant Add-on: Crypto Inspect
# https://developers.home-assistant.io/docs/add-ons
# syntax=docker/dockerfile:1.4

ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base-debian:bookworm
FROM ${BUILD_FROM}

# Labels
LABEL maintainer="Crypto Inspect" \
    org.opencontainers.image.title="Crypto Inspect" \
    org.opencontainers.image.description="Cryptocurrency data collector for Home Assistant"

# Install build and runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gfortran \
    pkg-config \
    libopenblas-dev \
    python3-dev \
    python3-pip \
    curl \
    libffi-dev \
    libssl-dev \
    postgresql-client \
    libopenblas0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Remove PEP 668 restriction to allow system-wide pip install
RUN rm -f /usr/lib/python3.11/EXTERNALLY-MANAGED

# Install uv package manager
ENV UV_INSTALL_DIR="/opt/uv" \
    UV_NO_PROGRESS=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && ln -s /opt/uv/uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies system-wide
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system --python /usr/bin/python3 .

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random

# Copy application code
COPY --chown=root:root src ./src
COPY --chown=root:root alembic ./alembic
COPY --chown=root:root alembic.ini ./

# Copy custom_components for user installation
COPY --chown=root:root custom_components /custom_components

# Copy rootfs (s6-overlay service scripts)
COPY rootfs /

# Set permissions for s6-overlay scripts
RUN find /etc/s6-overlay -type f -exec chmod 755 {} + 2>/dev/null || true \
    && find /etc/cont-init.d -type f -exec chmod 755 {} + 2>/dev/null || true \
    && find /etc/services.d -type f -name "run" -exec chmod 755 {} + 2>/dev/null || true \
    && find /etc/services.d -type f -name "finish" -exec chmod 755 {} + 2>/dev/null || true

# Create data directory for SQLite
RUN mkdir -p /data && chmod 755 /data

# Cleanup build dependencies to reduce image size
RUN apt-get purge -y --auto-remove \
    build-essential \
    gfortran \
    pkg-config \
    libopenblas-dev \
    python3-dev \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* /var/tmp/* \
    && find /var/log -type f -delete \
    && find /usr -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

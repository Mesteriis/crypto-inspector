# Home Assistant Add-on: Crypto Inspect
# https://developers.home-assistant.io/docs/add-ons

ARG BUILD_FROM
FROM ${BUILD_FROM}

# Install system dependencies
RUN apk add --no-cache \
    postgresql-client \
    build-base \
    python3-dev \
    libffi-dev \
    openssl-dev

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

# Copy dependency files and install
COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application code
COPY src ./src
COPY alembic ./alembic
COPY alembic.ini ./

# Copy rootfs (s6-overlay service scripts)
COPY rootfs /

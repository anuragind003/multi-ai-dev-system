# app/Dockerfile
# Multi-stage Dockerfile for FastAPI application with optimization.

# --- Stage 1: Builder ---
# Use a full Python image for building dependencies
FROM python:3.9-slim-buster as builder

# Set environment variables
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements file and install dependencies
# Use --no-cache-dir to save space
# Use --upgrade pip to ensure latest pip
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# --- Stage 2: Runner ---
# Use a smaller, production-ready base image
FROM python:3.9-slim-buster as runner

# Set environment variables
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ARG APP_PORT=8000
ENV APP_PORT=${APP_PORT}

# Set working directory
WORKDIR /app

# Copy only the installed packages from the builder stage
COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . /app

# Expose the application port
EXPOSE ${APP_PORT}

# Health check for Docker (used by docker-compose)
HEALTHCHECK --interval=30s --timeout=10s --retries=5 \
  CMD curl -f http://localhost:${APP_PORT}/health || exit 1

# Command to run the application using Uvicorn
# Use --host 0.0.0.0 to make it accessible from outside the container
# Use --log-level info for production logging
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "${APP_PORT}", "--log-level", "info"]
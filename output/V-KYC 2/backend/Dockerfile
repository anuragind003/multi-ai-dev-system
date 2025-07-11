# Stage 1: Builder - Install dependencies and build any necessary artifacts
FROM python:3.9-slim-buster AS builder

# Set environment variables
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

# Create and set working directory
WORKDIR /app

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file and install dependencies
COPY ./backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Runner - Copy application code and run
FROM python:3.9-slim-buster AS runner

# Set environment variables
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

# Create and set working directory
WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages

# Copy application code
COPY ./backend/ .

# Expose the port the application runs on
EXPOSE 8000

# Health check for Docker
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application using Gunicorn for production
# Using --bind 0.0.0.0:8000 for external access
# --workers: Number of worker processes (e.g., 2 * CPU_CORES + 1)
# --worker-class: Type of worker (uvicorn.workers.UvicornWorker for async)
# --log-level: Set logging level (info, debug, warning, error, critical)
CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:8000", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--log-level", "info"]
# Stage 1: Builder - Install dependencies and build artifacts
FROM python:3.10-slim-buster AS builder

# Set working directory
WORKDIR /app

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy poetry.lock* and pyproject.toml to cache dependencies
COPY pyproject.toml poetry.lock* ./

# Install Poetry and dependencies
RUN pip install poetry
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-root

# Copy application code
COPY ./app /app/app

# Stage 2: Runner - Create a minimal image for production
FROM python:3.10-slim-buster AS runner

# Set working directory
WORKDIR /app

# Create a non-root user for security
RUN adduser --system --group appuser
USER appuser

# Copy only the necessary files from the builder stage
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/uvicorn
COPY --from=builder /usr/local/bin/gunicorn /usr/local/bin/gunicorn
COPY --from=builder /app/app /app/app

# Expose the port the application will run on
EXPOSE 8000

# Health check endpoint for Kubernetes/Docker Compose
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 CMD curl -f http://localhost:8000/health || exit 1

# Command to run the application using Gunicorn with Uvicorn workers
# Using --bind 0.0.0.0:8000 to listen on all interfaces
# Using --workers for concurrency (adjust based on CPU cores)
# Using --worker-class uvicorn.workers.UvicornWorker for async support
CMD ["gunicorn", "app.main:app", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
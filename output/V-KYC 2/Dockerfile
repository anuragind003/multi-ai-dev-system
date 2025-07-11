# Stage 1: Build - Python application
FROM python:3.10-slim-buster AS builder

# Set environment variables
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create and set working directory
WORKDIR /app

# Copy poetry.lock* and pyproject.toml to install dependencies
COPY pyproject.toml poetry.lock* ./

# Install Poetry
RUN pip install poetry

# Configure Poetry for virtual environment in-project
RUN poetry config virtualenvs.in-project true

# Install project dependencies
RUN poetry install --no-dev --no-root

# Copy application source code
COPY app/ ./app/

# Stage 2: Production - Runtime
FROM python:3.10-slim-buster AS production

# Set environment variables
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

# Install runtime dependencies (if any specific ones are needed that weren't in builder)
# For a simple FastAPI app, often none beyond what's in slim-buster
# If using psycopg2-binary, no libpq-dev needed here.
# If using a non-binary version, libpq-dev would be needed in builder and libpq5 in production.

# Create and set working directory
WORKDIR /app

# Copy only the necessary files from the builder stage
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/app ./app
COPY --from=builder /app/pyproject.toml /app/poetry.lock* ./

# Add .venv to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
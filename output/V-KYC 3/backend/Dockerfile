# Stage 1: Builder
FROM python:3.10-slim-buster AS builder

# Set environment variables
ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1 \
    PYSETUP_PATH="/opt/pysetup" \
    VIRTUAL_ENV="/opt/pysetup/.venv"

# Install system dependencies for Poetry and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - --version 1.8.2

# Add Poetry to PATH
ENV PATH="${POETRY_HOME}/bin:${VIRTUAL_ENV}/bin:${PATH}"

# Copy project files
WORKDIR /app
COPY pyproject.toml poetry.lock ./

# Install project dependencies
RUN poetry install --no-root --no-dev

# Stage 2: Runner
FROM python:3.10-slim-buster AS runner

# Set environment variables
ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies for runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user and group
RUN groupadd --system --gid 1001 appgroup && \
    useradd --system --uid 1001 --gid appgroup appuser

# Set working directory
WORKDIR /app

# Copy virtual environment from builder stage
COPY --from=builder /opt/pysetup/.venv /opt/pysetup/.venv

# Add virtual environment to PATH
ENV PATH="/opt/pysetup/.venv/bin:$PATH"

# Copy application code
COPY backend/app ./app
COPY backend/pyproject.toml ./pyproject.toml # Copy pyproject.toml for metadata/versioning if needed by app

# Set ownership to the non-root user
RUN chown -R appuser:appgroup /app

# Switch to the non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 CMD curl -f http://localhost:8000/health || exit 1

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
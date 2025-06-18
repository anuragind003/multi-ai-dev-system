# Dockerfile for a secure, isolated code execution environment
# Base image with Python pre-installed
FROM python:3.9-slim

# --- Install Node.js, npm, and essential build tools ---
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    nodejs \
    npm \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# --- Install global JavaScript/TypeScript tools ---
# This includes the TypeScript compiler (tsc) and ESLint for linting.
RUN npm install -g typescript eslint

# --- Install Python tools ---
# This includes common linters and the pytest testing framework.
RUN pip install --no-cache-dir \
    pytest \
    pytest-cov \
    flake8 \
    pylint \
    black \
    pycodestyle

# --- Create a non-root user for sandboxed execution ---
# Running as a non-root user is a critical security best practice.
RUN useradd -ms /bin/bash executor

# Switch to the non-root user
USER executor

# --- Set the working directory ---
# Code will be mounted and executed within this directory.
WORKDIR /app

# Set a default command to keep the container running if needed for interactive use,
# but we will typically override this with our specific commands.
CMD ["/bin/bash"]
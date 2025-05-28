FROM python:3.9-slim-buster

WORKDIR /app

# Install system dependencies required for psycopg2 and other utilities
# libpq-dev is needed for psycopg2-binary to compile against PostgreSQL client libraries
# gcc is needed for compiling C extensions
# netcat-traditional is a useful utility, often used for health checks or waiting for services
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file first to leverage Docker's build cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire application code
COPY . .

# Set environment variables for Flask
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_ENV=production # Set to 'development' for local dev, 'production' for deployment

# Expose the port the Flask application will run on
EXPOSE 5000

# Command to run the application using Gunicorn, a production-ready WSGI server.
# Assumes your Flask app instance is named 'app' within 'app.py'.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
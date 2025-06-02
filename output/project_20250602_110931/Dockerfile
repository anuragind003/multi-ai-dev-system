# Use a lightweight Python base image for the Flask application.
# python:3.9-slim-buster provides a minimal Debian-based image with Python 3.9,
# which is good for production to keep image size small.
FROM python:3.9-slim-buster

# Set the working directory inside the container.
# All subsequent commands will be executed relative to this directory.
WORKDIR /app

# Prevent Python from writing .pyc files to disk.
# This helps keep the image clean and reduces unnecessary disk I/O.
ENV PYTHONDONTWRITEBYTECODE 1

# Ensure that the Python output is sent straight to stdout/stderr.
# This is crucial for Docker logging and debugging.
ENV PYTHONUNBUFFERED 1

# Copy the requirements file into the working directory.
# Copying it separately before the rest of the application code allows Docker
# to cache this layer. If requirements.txt doesn't change, subsequent builds
# will use the cached layer, speeding up the build process.
COPY requirements.txt .

# Install Python dependencies specified in requirements.txt.
# --no-cache-dir: Prevents pip from storing downloaded packages in a cache,
#                 further reducing the final image size.
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire application source code into the working directory.
# The '.' on the left refers to the current directory on the host machine
# where the Dockerfile is located. The '.' on the right refers to the
# WORKDIR (/app) inside the container.
COPY . .

# Expose port 5000. This informs Docker that the container listens on the
# specified network port at runtime. It does not actually publish the port.
# To publish the port, use the -p flag with `docker run` (e.g., -p 5000:5000).
EXPOSE 5000

# Define the command to run the application when the container starts.
# We use Gunicorn, a production-ready WSGI HTTP server for Python, to serve
# the Flask application.
# -w 4: Specifies 4 worker processes. A common heuristic is (2 * CPU_CORES) + 1.
#       Adjust based on your server's CPU and expected load.
# -b 0.0.0.0:5000: Binds Gunicorn to all network interfaces on port 5000,
#                  making the application accessible from outside the container.
# app:app: Specifies the module and the Flask application instance.
#          It assumes your Flask application instance is named 'app' and is
#          defined within a file named 'app.py' (e.g., `from flask import Flask; app = Flask(__name__)`).
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
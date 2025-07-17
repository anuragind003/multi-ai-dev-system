import os

# Gunicorn configuration file for production deployments

# Bind to 0.0.0.0 to listen on all interfaces
bind = "0.0.0.0:8000"

# Number of worker processes
# A common formula is (2 * CPU_CORES) + 1
# Adjust based on your server's CPU cores and application's I/O bound nature.
workers = int(os.getenv("GUNICORN_WORKERS", "4"))

# Worker class: uvicorn.workers.UvicornWorker for ASGI applications
worker_class = "uvicorn.workers.UvicornWorker"

# Timeout for graceful worker shutdown (seconds)
timeout = int(os.getenv("GUNICORN_TIMEOUT", "30"))

# Maximum requests a worker will process before restarting
# This helps to mitigate memory leaks. Set to 0 for unlimited.
max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", "1000"))
max_requests_jitter = int(os.getenv("GUNICORN_MAX_REQUESTS_JITTER", "50"))

# Logging
# Access log file
accesslog = os.getenv("GUNICORN_ACCESSLOG", "-") # "-" means stdout
# Error log file
errorlog = os.getenv("GUNICORN_ERRORLOG", "-") # "-" means stderr
# Log level: debug, info, warning, error, critical
loglevel = os.getenv("GUNICORN_LOGLEVEL", "info")

# Daemonize the Gunicorn process (run in background)
# Set to False for containerized environments where the container's main process should be Gunicorn.
daemon = False

# PID file for the master process
# pidfile = "/tmp/gunicorn.pid" # Not typically needed in containers

# User and group to run as (if not root)
# user = "appuser"
# group = "appuser"

# Enable graceful restarts
# reload = True # Only for development, not for production

# Server hooks (optional)
# def post_fork(server, worker):
#     server.log.info("Worker spawned (pid: %s)", worker.pid)

# def pre_fork(server, worker):
#     pass

# def pre_exec(server):
#     server.log.info("Forked child, re-executing.")

# def when_ready(server):
#     server.log.info("Server is ready. Spawning workers")

# def worker_abort(worker):
#     worker.log.info("worker received SIGABRT signal")

# def worker_exit(worker):
#     worker.log.info("worker exited (pid: %s)", worker.pid)

# def on_starting(server):
#     server.log.info("Starting Gunicorn server...")

# def on_reload(server):
#     server.log.info("Server reloading...")
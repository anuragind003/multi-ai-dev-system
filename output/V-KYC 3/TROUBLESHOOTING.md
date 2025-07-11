# Troubleshooting Guide and Runbook

This document provides common troubleshooting steps and runbook procedures for the FastAPI application and its associated infrastructure.

## Table of Contents

1.  [General Troubleshooting Steps](#1-general-troubleshooting-steps)
2.  [Application (FastAPI) Issues](#2-application-fastapi-issues)
3.  [Database (PostgreSQL) Issues](#3-database-postgresql-issues)
4.  [Nginx (Reverse Proxy) Issues](#4-nginx-reverse-proxy-issues)
5.  [Monitoring (Prometheus/Grafana) Issues](#5-monitoring-prometheusgrafana-issues)
6.  [CI/CD Pipeline Issues](#6-cicd-pipeline-issues)
7.  [Docker/Container Issues](#7-dockercontainer-issues)
8.  [Backup and Restore Procedures](#8-backup-and-restore-procedures)

---

## 1. General Troubleshooting Steps

Before diving into specific components, try these general steps:

*   **Check Logs:** Always start by checking the logs of the affected service.
    *   For a specific service: `docker compose logs <service_name>` (e.g., `docker compose logs app`)
    *   For all services: `docker compose logs`
    *   For production, consider using a centralized logging solution.
*   **Check Service Status:** Verify if the Docker containers are running.
    *   `docker compose ps` (for services defined in `docker-compose.yml` or `docker-compose.prod.yml`)
    *   `docker ps` (for all running containers)
*   **Restart Service:** A simple restart can often resolve transient issues.
    *   `docker compose restart <service_name>`
*   **Check Resource Usage:** High CPU/memory usage can indicate a problem.
    *   `docker stats`
    *   On the host: `top`, `htop`, `free -h`
*   **Verify Network Connectivity:** Ensure containers can communicate with each other and with external services.
    *   `docker compose exec <service_name> ping <another_service_name>` (e.g., `docker compose exec app ping db`)
    *   `docker compose exec <service_name> curl http://<another_service_name>:<port>/health`

---

## 2. Application (FastAPI) Issues

**Symptoms:**
*   API endpoints returning 5xx errors.
*   Application not starting or crashing.
*   Slow response times.

**Troubleshooting Steps:**

1.  **Check App Logs:**
    ```bash
    docker compose logs app
    ```
    Look for Python tracebacks, database connection errors, or specific error messages from your FastAPI code.
2.  **Verify Database Connection:**
    *   Ensure `DATABASE_URL` in `.env` (or secrets in prod) is correct.
    *   Check if the `db` service is healthy: `docker compose ps`
    *   Try connecting from inside the app container:
        ```bash
        docker compose exec app bash
        # Inside the container:
        # pip install psycopg2-binary # if not already installed
        # python -c "import psycopg2; psycopg2.connect('YOUR_DATABASE_URL')"
        ```
3.  **Check Health Endpoint:**
    *   `curl http://localhost:8000/health` (local)
    *   `curl https://your-domain.com/health` (production, via Nginx)
    *   If it fails, the app is not responding correctly.
4.  **Restart Application:**
    ```bash
    docker compose restart app
    ```
5.  **Rebuild Application Image:** If code changes aren't reflected or dependencies are an issue.
    ```bash
    docker compose build app
    docker compose up -d app
    ```

---

## 3. Database (PostgreSQL) Issues

**Symptoms:**
*   Application unable to connect to the database.
*   Database service not starting.
*   Data corruption or unexpected data.

**Troubleshooting Steps:**

1.  **Check DB Logs:**
    ```bash
    docker compose logs db
    ```
    Look for errors related to startup, disk space, or connection issues.
2.  **Verify DB Health Check:**
    ```bash
    docker compose ps
    ```
    Check the `Health` column for the `db` service. It should be `healthy`.
3.  **Check Port Connectivity:**
    *   From the host: `nc -z localhost 5432` (local)
    *   From the app container: `docker compose exec app nc -z db 5432`
4.  **Check Disk Space:**
    *   On the host machine where Docker volumes are stored: `df -h`
    *   If the volume is full, the DB might not start or perform poorly.
5.  **Access DB Shell (for advanced debugging):**
    ```bash
    docker compose exec db psql -U <POSTGRES_USER> -d <POSTGRES_DB>
    ```
    (Use credentials from `.env` or secrets)
6.  **Restart Database:**
    ```bash
    docker compose restart db
    ```
    **Caution:** Restarting might not fix data corruption. If data is corrupted, a restore from backup might be necessary.

---

## 4. Nginx (Reverse Proxy) Issues

**Symptoms:**
*   Website inaccessible (502 Bad Gateway, 404 Not Found, connection refused).
*   HTTPS not working.

**Troubleshooting Steps:**

1.  **Check Nginx Logs:**
    ```bash
    docker compose logs nginx
    ```
    Look for `error.log` entries, especially `upstream` errors (indicating issues with the backend app).
2.  **Verify Nginx Configuration:**
    *   Check `nginx/nginx.conf` for syntax errors.
    *   Test config: `docker compose exec nginx nginx -t`
    *   Reload config: `docker compose exec nginx nginx -s reload` (after fixing config)
3.  **Check Nginx Service Status:**
    ```bash
    docker compose ps
    ```
    Ensure `nginx` service is `Up`.
4.  **Verify App Connectivity from Nginx:**
    *   From inside the Nginx container, try to `curl` the app service:
        ```bash
        docker compose exec nginx bash
        # Inside container:
        curl http://app:8000/health
        ```
    *   If this fails, Nginx cannot reach the application. Check `app` service status and network.
5.  **SSL/TLS Issues:**
    *   Verify certificate paths in `nginx.conf` are correct and files exist.
    *   Check certificate expiration dates.
    *   Use online SSL checkers (e.g., SSL Labs) to diagnose issues.

---

## 5. Monitoring (Prometheus/Grafana) Issues

**Symptoms:**
*   No metrics appearing in Prometheus or Grafana.
*   Grafana dashboards empty or showing "No Data".
*   Prometheus targets down.

**Troubleshooting Steps:**

1.  **Check Prometheus Logs:**
    ```bash
    docker compose logs prometheus
    ```
    Look for errors related to configuration, scraping, or storage.
2.  **Check Prometheus UI:**
    *   Access `http://your-prod-host:9090`.
    *   Go to `Status` -> `Targets`. Verify that `fastapi_app`, `cadvisor`, `node_exporter` (if configured) targets are `UP`.
    *   If a target is `DOWN`, check the error message in Prometheus UI.
    *   Ensure the `metrics_path` and `targets` in `prometheus/prometheus.yml` are correct.
3.  **Check Grafana Logs:**
    ```bash
    docker compose logs grafana
    ```
    Look for errors related to data source connection or dashboard loading.
4.  **Verify Grafana Data Source:**
    *   Log into Grafana (`http://your-prod-host:3000`).
    *   Go to `Connections` -> `Data sources`. Ensure Prometheus data source is configured correctly and tests successfully.
    *   The URL for Prometheus should be `http://prometheus:9090` (from Grafana's perspective within the Docker network).
5.  **Check App Metrics Endpoint:**
    *   Ensure your FastAPI app exposes metrics at `/metrics` (or configured path).
    *   `curl http://app:8000/metrics` (from another container or host if port is exposed).

---

## 6. CI/CD Pipeline Issues

**Symptoms:**
*   GitHub Actions workflow failing.
*   Builds not starting.
*   Deployment failures.

**Troubleshooting Steps:**

1.  **Review Workflow Logs:**
    *   Go to your GitHub repository -> `Actions` tab.
    *   Click on the failed workflow run.
    *   Expand the failed job and step to see detailed error messages.
2.  **Lint/Format Failures:**
    *   Run `poetry run black --check .`, `poetry run flake8 .`, `poetry run isort --check-only .` locally to reproduce and fix issues.
3.  **Test Failures:**
    *   Run `poetry run pytest tests/` locally to debug test failures.
    *   Ensure your local test environment matches the CI environment (Python version, dependencies, DB setup).
4.  **Build/Push Failures:**
    *   Check Dockerfile syntax.
    *   Ensure GitHub Token has `packages: write` permission.
    *   Check for network issues during image push.
5.  **Vulnerability Scan Failures (Trivy):**
    *   Review the Trivy report in the workflow logs.
    *   Identify the critical/high vulnerabilities.
    *   Update base images, dependencies, or address the reported issues in your application code.
6.  **Deployment Failures:**
    *   Check SSH connection details (`SSH_PRIVATE_KEY`, `PROD_USER`, `PROD_HOST` GitHub Secrets).
    *   Verify the remote path for deployment.
    *   Check `docker compose -f docker-compose.prod.yml` commands for errors.
    *   Ensure Docker and Docker Compose are running on the production host.
    *   Check permissions on the remote server for creating/writing files (e.g., secrets files).

---

## 7. Docker/Container Issues

**Symptoms:**
*   Containers not starting.
*   Containers exiting unexpectedly.
*   Docker daemon issues.

**Troubleshooting Steps:**

1.  **Check `docker compose ps`:** See the status column. `Exited` means it crashed.
2.  **Check `docker compose logs <service_name>`:** Look for the reason for the exit.
3.  **Check Docker Daemon Status:**
    *   `sudo systemctl status docker` (Linux)
    *   If not running, start it: `sudo systemctl start docker`
4.  **Disk Space:**
    *   `docker system df -v` to check Docker disk usage.
    *   `docker system prune -a` (DANGER: removes all stopped containers, unused networks, dangling images, and build cache) to free up space. Use with caution.
5.  **Volume Permissions:**
    *   Ensure the user inside the container (`appuser`) has correct permissions to write to mounted volumes if necessary.
    *   Check host directory permissions for volumes.
6.  **Port Conflicts:**
    *   Ensure no other process on the host is using the ports required by your containers (e.g., 80, 443, 8000, 5432, 3000, 9090).
    *   `sudo netstat -tulnp | grep <port>`

---

## 8. Backup and Restore Procedures

These procedures are critical for disaster recovery.

### 8.1. Database Backup

**Purpose:** To create a snapshot of your PostgreSQL database.

**Procedure:**

1.  **Connect to your production server via SSH.**
2.  **Navigate to your application's deployment directory.**
    ```bash
    cd /path/to/your/app/directory
    ```
3.  **Optional: Stop the application service for consistency (recommended for large databases or critical backups).**
    ```bash
    docker compose -f docker-compose.prod.yml stop app
    ```
4.  **Execute the `pg_dump` command from within the `db` container.**
    *   Replace `produser` with your actual PostgreSQL user.
    *   Replace `prod_db` with your actual database name.
    *   Replace `/path/to/backup/` with a secure, persistent location on your host machine.
    ```bash
    docker compose -f docker-compose.prod.yml exec db pg_dump -U produser prod_db > /path/to/backup/db_backup_$(date +%Y%m%d_%H%M%S).sql
    ```
    *   **Note on `pg_dump`:** If your database password is required, you might need to set the `PGPASSWORD` environment variable before the `docker compose exec` command, or use a `.pgpass` file. For Docker secrets, `pg_dump` should pick it up automatically if the user is configured correctly.
5.  **Verify the backup file size and content.**
    ```bash
    ls -lh /path/to/backup/db_backup_*.sql
    head -n 20 /path/to/backup/db_backup_*.sql
    ```
6.  **Optional: Restart the application service if you stopped it.**
    ```bash
    docker compose -f docker-compose.prod.yml start app
    ```
7.  **Crucial: Transfer the backup file to an offsite, secure storage location (e.g., S3, Google Cloud Storage, another server).** This protects against host failure.

### 8.2. Database Restore

**Purpose:** To restore the PostgreSQL database from a backup file. Use this in case of data loss or corruption.

**Procedure:**

1.  **Connect to your production server via SSH.**
2.  **Navigate to your application's deployment directory.**
    ```bash
    cd /path/to/your/app/directory
    ```
3.  **Ensure your backup file is present on the server in an accessible location.**
    *   If it's offsite, download it first.
    ```bash
    # Example: scp /path/to/local/backup.sql your_user@your_prod_host:/path/to/your/app/directory/
    ```
4.  **Stop the application and database services.** This is critical to prevent data inconsistencies during restore.
    ```bash
    docker compose -f docker-compose.prod.yml stop app db
    ```
5.  **Remove the existing database data volume.** **WARNING: This will permanently delete all current data in the database.** Only proceed if you are certain you want to replace the current data with the backup.
    ```bash
    docker volume rm fastapi-operational-infrastructure_db_data # Replace with your actual volume name (check `docker volume ls`)
    ```
6.  **Start only the database service.** This will create a new, empty data volume.
    ```bash
    docker compose -f docker-compose.prod.yml up -d db
    ```
7.  **Wait for the database service to become healthy.** This might take a few seconds to a minute.
    ```bash
    echo "Waiting for database to be ready..."
    sleep 15 # Adjust as needed, or use a loop with pg_isready check
    docker compose -f docker-compose.prod.yml exec db pg_isready -U produser -d prod_db
    ```
8.  **Restore the database from the backup file.**
    *   Replace `produser` and `prod_db` with your actual credentials.
    *   Replace `/path/to/backup/db_backup_latest.sql` with the actual path to your backup file.
    ```bash
    docker compose -f docker-compose.prod.yml exec -T db psql -U produser prod_db < /path/to/backup/db_backup_latest.sql
    ```
    *   The `-T` flag for `docker exec` is important for piping input correctly.
9.  **Verify the data integrity** by checking some records via `psql` or your application.
10. **Start the application service.**
    ```bash
    docker compose -f docker-compose.prod.yml start app
    ```
11. **Monitor logs** for both `db` and `app` services to ensure everything is functioning correctly after the restore.
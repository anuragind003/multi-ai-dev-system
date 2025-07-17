# Troubleshooting and Runbook

This document provides guidance for troubleshooting common issues and outlines standard operational procedures for the FastAPI Operational Infrastructure Demo.

## Table of Contents

1.  [General Troubleshooting Steps](#1-general-troubleshooting-steps)
2.  [Common Issues and Solutions](#2-common-issues-and-solutions)
    *   [Application Not Starting](#application-not-starting)
    *   [Database Connection Issues](#database-connection-issues)
    *   [API Endpoints Not Responding](#api-endpoints-not-responding)
    *   [High CPU/Memory Usage](#high-cpumemory-usage)
    *   [Monitoring Data Missing/Incorrect](#monitoring-data-missingincorrect)
    *   [CI/CD Pipeline Failures](#cicd-pipeline-failures)
    *   [Deployment Failures](#deployment-failures)
3.  [Runbook Procedures](#3-runbook-procedures)
    *   [Restarting Services](#restarting-services)
    *   [Scaling Application Instances](#scaling-application-instances)
    *   [Performing a Database Backup](#performing-a-database-backup)
    *   [Restoring a Database from Backup](#restoring-a-database-from-backup)
    *   [Rolling Back a Deployment](#rolling-back-a-deployment)
    *   [Applying Database Migrations](#applying-database-migrations)
4.  [Accessing Logs and Metrics](#4-accessing-logs-and-metrics)

---

## 1. General Troubleshooting Steps

When encountering an issue, follow these general steps:

1.  **Check Logs**: This is the first and most crucial step.
    *   For Docker Compose: `docker compose logs <service_name>` (e.g., `docker compose logs app`).
    *   For production/staging: Access centralized logging (e.g., ELK, Grafana Loki, CloudWatch Logs).
2.  **Check Service Status**:
    *   For Docker Compose: `docker compose ps`. Look for services that are `unhealthy` or `exited`.
    *   Check health endpoints: `GET /health`, `GET /live`, `GET /ready`.
3.  **Check Resource Usage**:
    *   `docker stats` for container-level CPU/memory.
    *   Prometheus/Grafana dashboards for historical trends and current resource consumption.
4.  **Verify Network Connectivity**:
    *   Ensure containers can communicate with each other (e.g., app to db).
    *   Check firewall rules if applicable.
5.  **Review Recent Changes**:
    *   What was the last deployment?
    *   Were any configuration changes made?
    *   Check CI/CD pipeline history for recent failures.
6.  **Reproduce the Issue**: If possible, try to reproduce the issue in a development or staging environment.

## 2. Common Issues and Solutions

### Application Not Starting

*   **Symptoms**: `docker compose ps` shows `app` service as `exited` or `unhealthy`. Logs show errors like "Address already in use", "ModuleNotFoundError", "Permission Denied".
*   **Troubleshooting**:
    *   **Check `app` service logs**: `docker compose logs app`. Look for Python tracebacks.
    *   **Port conflict**: If "Address already in use", another process on the host might be using port 8000. Stop it or change the port mapping in `docker-compose.yml`.
    *   **Missing dependencies**: Ensure `app/requirements.txt` is complete and `pip install` ran successfully in the Docker build.
    *   **Environment variables**: Verify `.env` file is correctly configured and loaded.
    *   **Permissions**: Ensure the `appuser` in `Dockerfile` has read access to `/app`.
*   **Solution**: Address the specific error in the logs. Rebuild the image (`docker compose build app`) if code or dependency changes were made.

### Database Connection Issues

*   **Symptoms**: Application logs show "Failed to connect to database", "Connection refused", "Authentication failed". `db` service might be `unhealthy`.
*   **Troubleshooting**:
    *   **Check `db` service logs**: `docker compose logs db`.
    *   **Database health**: Check `db` service health status (`docker compose ps`).
    *   **Credentials**: Verify `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` in `.env` match the database configuration.
    *   **Host/Port**: Ensure `DATABASE_URL` in `.env` points to the correct host (`db` for Docker Compose) and port (5432).
    *   **Network**: Ensure `app` and `db` services are on the same Docker network.
*   **Solution**: Correct credentials/host in `.env`. Restart `db` service if it's unhealthy.

### API Endpoints Not Responding (5xx errors)

*   **Symptoms**: API calls return 500 Internal Server Error, or timeout.
*   **Troubleshooting**:
    *   **Application logs**: Check `docker compose logs app` for specific error messages and tracebacks.
    *   **Readiness probe**: Check `/ready` endpoint. If it's failing, it indicates an issue with an external dependency (e.g., database).
    *   **Resource limits**: Check if the application is hitting CPU/memory limits (via `docker stats` or Grafana).
*   **Solution**: Debug the specific error in the application code. Scale up resources if limits are being hit.

### High CPU/Memory Usage

*   **Symptoms**: Application performance degrades, response times increase, `docker stats` shows high resource consumption.
*   **Troubleshooting**:
    *   **Grafana Dashboards**: Use the FastAPI dashboard to identify which endpoints or operations are consuming most resources.
    *   **Application logs**: Look for repeated errors or long-running queries.
    *   **Profiling**: If possible, use Python profiling tools (e.g., `cProfile`) to identify bottlenecks in the code.
*   **Solution**: Optimize inefficient code/queries. Scale up application instances (`replicas` in `docker-compose.prod.yml`). Increase resource limits.

### Monitoring Data Missing/Incorrect

*   **Symptoms**: Grafana dashboards show "No Data", or metrics are not updating.
*   **Troubleshooting**:
    *   **Prometheus Targets**: Go to Prometheus UI (`http://localhost:9090/targets`) and check if `fastapi_app` target is `UP`. If not, check `app` service health and network.
    *   **Prometheus Logs**: `docker compose logs prometheus`.
    *   **Grafana Data Source**: In Grafana, check `Configuration -> Data Sources` to ensure Prometheus is correctly configured and reachable.
    *   **Dashboard Queries**: Verify the queries in your Grafana dashboard are correct and match the metric names.
*   **Solution**: Ensure `app` service is running and its `/metrics` endpoint is accessible. Verify Prometheus configuration and Grafana data source.

### CI/CD Pipeline Failures

*   **Symptoms**: GitHub Actions workflow fails at a specific step.
*   **Troubleshooting**:
    *   **Review Job Logs**: Click on the failed job in GitHub Actions to see detailed logs.
    *   **Step-specific errors**:
        *   **Linting/Formatting**: Check output for specific `black`, `flake8`, `isort` errors.
        *   **Security Scan**: Review Bandit/Trivy reports (uploaded as artifacts) for findings.
        *   **Tests**: Check `pytest` output for failed tests and tracebacks.
        *   **Build/Push**: Look for Docker build errors or registry authentication issues.
        *   **Deployment**: Check SSH connection errors or commands failing on the remote server.
    *   **Secrets**: Ensure all required GitHub Secrets are correctly configured and accessible to the workflow.
*   **Solution**: Fix code quality issues, address security vulnerabilities, fix failing tests, or correct deployment scripts/secrets.

### Deployment Failures

*   **Symptoms**: Application not updated on staging/production, old version still running, or new deployment fails to start.
*   **Troubleshooting**:
    *   **CI/CD Logs**: Review the `deploy_staging` job logs in GitHub Actions for SSH errors or command failures on the remote host.
    *   **Remote Server Logs**: SSH into the staging server and check Docker logs (`docker logs <container_id>`) and `docker compose ps` for the deployed services.
    *   **Image Pull**: Ensure the server can pull the new Docker image from the registry (check `docker pull` command output on the server).
    *   **Resource Availability**: Ensure the server has enough resources (CPU, memory, disk space) for the new containers.
*   **Solution**: Address network issues, authentication problems, or resource constraints. Manually pull the image and run `docker compose up -d --force-recreate` on the server if needed.

## 3. Runbook Procedures

### Restarting Services

*   **Individual Service (e.g., app)**:
    ```bash
    docker compose restart app
    ```
*   **All Services**:
    ```bash
    docker compose restart
    ```
*   **Force Recreate (for new image/config changes)**:
    ```bash
    docker compose up -d --force-recreate <service_name_optional>
    ```

### Scaling Application Instances

*   **Local Development (not typically scaled)**:
    Modify `docker-compose.yml` (not recommended for local dev).
*   **Staging/Production (using `docker-compose.prod.yml`)**:
    Modify the `replicas` count under the `deploy` section for the `app` service in `docker-compose.prod.yml`.
    ```yaml
    # Example in docker-compose.prod.yml
    services:
      app:
        deploy:
          replicas: 3 # Change this number
    ```
    Then apply the change:
    ```bash
    docker compose -f docker-compose.prod.yml up -d --scale app=3
    ```
    Or simply `docker compose -f docker-compose.prod.yml up -d` after changing `replicas` in the file.

### Performing a Database Backup

This procedure assumes PostgreSQL.

1.  **Access the database container**:
    ```bash
    docker compose exec db bash
    ```
2.  **Perform the dump**:
    ```bash
    pg_dump -U ${POSTGRES_USER} ${POSTGRES_DB} > /var/lib/postgresql/data/backup_$(date +%Y%m%d_%H%M%S).sql
    exit
    ```
    (Replace `${POSTGRES_USER}` and `${POSTGRES_DB}` with actual values from `.env`).
3.  **Copy backup to host**:
    ```bash
    docker compose cp db:/var/lib/postgresql/data/backup_YYYYMMDD_HHMMSS.sql ./db_backups/
    ```
    (Replace `YYYYMMDD_HHMMSS` with the actual timestamp).
4.  **Store backups securely**: Move the backup file to off-site storage or a dedicated backup solution.

### Restoring a Database from Backup

**WARNING**: This will overwrite existing data. Use with extreme caution.

1.  **Stop the application (optional but recommended)**:
    ```bash
    docker compose stop app
    ```
2.  **Copy backup file to the database container (if not already there)**:
    ```bash
    docker compose cp ./path/to/your/backup.sql db:/tmp/backup.sql
    ```
3.  **Access the database container**:
    ```bash
    docker compose exec db bash
    ```
4.  **Drop and recreate the database (or just clear tables)**:
    ```bash
    psql -U ${POSTGRES_USER} -c "DROP DATABASE IF EXISTS ${POSTGRES_DB};"
    psql -U ${POSTGRES_USER} -c "CREATE DATABASE ${POSTGRES_DB};"
    ```
5.  **Restore the database**:
    ```bash
    psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} < /tmp/backup.sql
    exit
    ```
6.  **Restart the application**:
    ```bash
    docker compose start app
    ```

### Rolling Back a Deployment

If a new deployment causes issues, you can roll back to a previous working image.

1.  **Identify the previous stable image tag**: Check your Docker registry (e.g., GitHub Container Registry) or CI/CD history for the SHA of the last known good deployment.
2.  **Update `docker-compose.prod.yml`**: Change the `image` tag for the `app` service to the previous stable tag.
    ```yaml
    # Example in docker-compose.prod.yml
    services:
      app:
        image: your-docker-registry/fastapi-app:previous_stable_sha # Change this
    ```
3.  **Redeploy**:
    ```bash
    docker compose -f docker-compose.prod.yml pull app # Pull the old image
    docker compose -f docker-compose.prod.yml up -d --force-recreate app
    ```
    Monitor logs and health checks after rollback.

### Applying Database Migrations

This assumes you are using a tool like Alembic for database migrations.

1.  **Ensure migration scripts are in the image**: Your `Dockerfile` should copy migration scripts if they are part of the application.
2.  **Run migration command**:
    ```bash
    docker compose exec app alembic upgrade head
    ```
    (Replace `alembic upgrade head` with your actual migration command).
    *   **Note**: For production, migrations should ideally be run as a separate step in CI/CD *before* the new application version is fully deployed, or as an init container in Kubernetes. For Docker Compose, `docker compose run --rm app alembic upgrade head` is safer as it runs in a new container.

## 4. Accessing Logs and Metrics

*   **Application Logs**:
    *   Local/Staging: `docker compose logs app`
    *   Production: Centralized logging system (e.g., ELK Stack, Grafana Loki, cloud provider logs).
*   **Prometheus Metrics**:
    *   Access Prometheus UI at `http://localhost:9090` (local) or `http://your-staging-ip:9090` (staging).
    *   Query metrics directly (e.g., `http_requests_total`).
*   **Grafana Dashboards**:
    *   Access Grafana UI at `http://localhost:3000` (local) or `http://your-staging-ip:3000` (staging).
    *   Explore pre-built or custom dashboards for application and infrastructure health.
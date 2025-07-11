# Troubleshooting and Runbook

This document serves as a runbook for common issues encountered with the FastAPI backend application and its infrastructure. It provides symptoms, potential causes, and resolution steps.

## Table of Contents

1.  [General Troubleshooting Steps](#1-general-troubleshooting-steps)
2.  [Application Issues](#2-application-issues)
    *   [500 Internal Server Error](#21-500-internal-server-error)
    *   [422 Unprocessable Entity (Validation Error)](#22-422-unprocessable-entity-validation-error)
    *   [Application Slow/Unresponsive](#23-application-slowunresponsive)
    *   [CORS Errors](#24-cors-errors)
3.  [Database Issues](#3-database-issues)
    *   [Database Connection Failed](#31-database-connection-failed)
    *   [Database Performance Degradation](#32-database-performance-degradation)
4.  [Container/Deployment Issues](#4-containerdeployment-issues)
    *   [Container Not Starting/Crashing](#41-container-not-startingcrashing)
    *   [Health Check Failing](#42-health-check-failing)
    *   [Nginx Proxy Issues](#43-nginx-proxy-issues)
    *   [Deployment Rollback](#44-deployment-rollback)
5.  [Monitoring Issues](#5-monitoring-issues)
    *   [Metrics Not Appearing in Prometheus/Grafana](#51-metrics-not-appearing-in-prometheusgrafana)
    *   [Grafana Dashboard Empty/No Data](#52-grafana-dashboard-emptyno-data)
6.  [CI/CD Issues](#6-cicd-issues)
    *   [Pipeline Failure](#61-pipeline-failure)
    *   [Image Build Failure](#62-image-build-failure)

---

## 1. General Troubleshooting Steps

Before diving into specific issues, follow these general steps:

1.  **Check Logs:** Always start by checking the logs of the affected component (application, database, Nginx, etc.).
    *   **Docker Compose:** `docker-compose logs <service_name>`
    *   **Kubernetes:** `kubectl logs <pod_name> -f`
2.  **Check Service Status:**
    *   **Docker Compose:** `docker-compose ps`
    *   **Kubernetes:** `kubectl get pods`, `kubectl describe pod <pod_name>`
3.  **Check Resource Utilization:** Use monitoring tools (Grafana, `docker stats`, `kubectl top`) to check CPU, memory, disk I/O.
4.  **Verify Network Connectivity:** Ensure components can reach each other (e.g., application to database).
    *   `docker exec <container_name> ping <target_host>`
    *   `kubectl exec -it <pod_name> -- ping <target_service>`
5.  **Review Recent Changes:** Has any code been deployed recently? Any infrastructure changes?

---

## 2. Application Issues

### 2.1 500 Internal Server Error

**Symptoms:**
*   API requests return HTTP 500 status code.
*   Generic "An unexpected error occurred" message.

**Potential Causes:**
*   Unhandled exceptions in application code.
*   Database connection issues (if not caught earlier).
*   External service dependency failure.
*   Incorrect environment variables.

**Resolution Steps:**
1.  **Check Application Logs:** Look for Python tracebacks in the backend container logs (`docker-compose logs backend` or `kubectl logs <backend-pod>`).
2.  **Verify Environment Variables:** Ensure all required environment variables are correctly set and accessible by the application.
3.  **Check Database Connectivity:** See [3.1 Database Connection Failed](#31-database-connection-failed).
4.  **Check External Dependencies:** If the application relies on other services (e.g., external APIs, message queues), verify their status.
5.  **Reproduce Locally:** Try to reproduce the error in a local development environment to debug with more tools.

### 2.2 422 Unprocessable Entity (Validation Error)

**Symptoms:**
*   API requests return HTTP 422 status code.
*   Response body contains details about validation errors (e.g., missing fields, incorrect data types).

**Potential Causes:**
*   Client sending malformed request body (e.g., missing required fields, wrong data types for Pydantic models).
*   API documentation (Swagger UI) might be outdated or misleading.

**Resolution Steps:**
1.  **Check Request Payload:** Verify the request body sent by the client matches the expected Pydantic model for the endpoint.
2.  **Consult API Docs:** Refer to `http://localhost:8000/docs` (or production URL) for the correct request schema.
3.  **Update Client:** If the client is sending incorrect data, update it to conform to the API's expectations.

### 2.3 Application Slow/Unresponsive

**Symptoms:**
*   High latency for API requests.
*   Requests timing out.
*   Application not responding to requests.

**Potential Causes:**
*   High CPU/memory usage on the application container.
*   Database performance bottlenecks (slow queries, high load).
*   Network latency.
*   Inefficient application code (e.g., N+1 queries, blocking I/O).
*   Insufficient number of Gunicorn workers.

**Resolution Steps:**
1.  **Check Monitoring (Grafana):** Look at application metrics (request latency, error rates), container resource usage (CPU, memory) for the backend.
2.  **Check Database Metrics:** Investigate database CPU, memory, active connections, and slow queries.
3.  **Scale Up/Out:**
    *   **Docker Compose:** Increase `GUNICORN_WORKERS` in `docker-compose.prod.yml` or scale the `backend` service (`docker-compose up -d --scale backend=X`).
    *   **Kubernetes:** Increase `replicas` in `k8s/backend-deployment.yaml` and apply (`kubectl apply -f ...`).
4.  **Profile Application:** Use profiling tools (e.g., `py-spy`, `cProfile`) to identify bottlenecks in the code.
5.  **Optimize Database Queries:** Review and optimize slow queries. Add indexes if necessary.

### 2.4 CORS Errors

**Symptoms:**
*   Frontend application receives "Access-Control-Allow-Origin" errors in the browser console.
*   Requests are blocked by the browser.

**Potential Causes:**
*   Frontend origin not listed in `CORS_ORIGINS` environment variable.
*   Incorrect CORS middleware configuration in `backend/app/main.py`.
*   Nginx not correctly passing CORS headers (less common if backend handles it).

**Resolution Steps:**
1.  **Verify `CORS_ORIGINS`:** Ensure the exact origin (including protocol and port) of your frontend application is listed in the `CORS_ORIGINS` environment variable for the backend.
2.  **Check Backend Logs:** Look for any CORS-related warnings or errors during startup.
3.  **Inspect Network Requests:** Use browser developer tools to inspect the `Origin` header in the request and `Access-Control-Allow-Origin` in the response.

---

## 3. Database Issues

### 3.1 Database Connection Failed

**Symptoms:**
*   Application logs show "database connection refused" or similar errors.
*   Database service health check failing.

**Potential Causes:**
*   Database container not running or crashed.
*   Incorrect `DATABASE_URL` (host, port, user, password, database name).
*   Network connectivity issues between application and database.
*   Database max connections limit reached.

**Resolution Steps:**
1.  **Check Database Container Status:**
    *   **Docker Compose:** `docker-compose ps db` or `docker-compose logs db`.
    *   **Kubernetes:** `kubectl get pods -l app=db`, `kubectl logs <db-pod>`.
2.  **Verify `DATABASE_URL`:** Double-check the `DATABASE_URL` in the backend's environment variables. Ensure host, port, user, password, and database name are correct.
3.  **Test Connectivity:**
    *   From the backend container: `docker exec -it <backend-container> bash` then `ping db` (or `ping <db_ip>`) and `psql -h db -U user -d mydatabase`.
    *   From a Kubernetes backend pod: `kubectl exec -it <backend-pod> -- bash` then `ping <db-service-name>` and `psql -h <db-service-name> -U user -d mydatabase`.
4.  **Check Database Logs:** Look for errors related to startup, authentication, or connection limits.
5.  **Restart Database:** If the database container is stuck, try restarting it.

### 3.2 Database Performance Degradation

**Symptoms:**
*   Slow application responses, especially for data-intensive operations.
*   High CPU/memory usage on the database server.
*   High number of active database connections.

**Potential Causes:**
*   Missing or inefficient database indexes.
*   Complex or unoptimized SQL queries.
*   Large data volumes.
*   Insufficient database resources (CPU, RAM, disk I/O).
*   Long-running transactions or locks.

**Resolution Steps:**
1.  **Monitor Database Metrics:** Use Grafana dashboards for PostgreSQL (e.g., `pg_exporter` metrics) to identify slow queries, high connection counts, and resource bottlenecks.
2.  **Analyze Slow Queries:** Enable slow query logging in PostgreSQL and analyze the logs. Use `EXPLAIN ANALYZE` for problematic queries.
3.  **Add/Optimize Indexes:** Create indexes on frequently queried columns, especially those used in `WHERE`, `JOIN`, `ORDER BY` clauses.
4.  **Optimize Application Queries:** Review ORM usage or raw SQL queries in the application code.
5.  **Scale Database Resources:** Increase CPU, memory, or disk IOPS for the database server.
6.  **Review Connection Pooling:** Ensure the application uses connection pooling effectively to manage database connections.

---

## 4. Container/Deployment Issues

### 4.1 Container Not Starting/Crashing

**Symptoms:**
*   `docker ps` shows container with `Exited` status.
*   `kubectl get pods` shows pod in `CrashLoopBackOff` or `Error` state.

**Potential Causes:**
*   Application startup error (e.g., syntax error, missing dependency, incorrect config).
*   Port conflict.
*   Insufficient resources (memory limits too low).
*   Incorrect entrypoint or command in Dockerfile.

**Resolution Steps:**
1.  **Check Container Logs:** This is the most important step. `docker logs <container_id>` or `kubectl logs <pod_name>`. Look for the first error message.
2.  **Check Dockerfile/Kubernetes Manifest:** Verify `CMD`, `ENTRYPOINT`, and `ports` in `Dockerfile` and `k8s/backend-deployment.yaml`.
3.  **Increase Resources:** If logs indicate out-of-memory errors, increase memory limits in `docker-compose.prod.yml` or `k8s/backend-deployment.yaml`.
4.  **Run Locally:** Try to build and run the Docker image locally (`docker build -t myapp . && docker run myapp`) to debug startup issues outside the orchestrator.

### 4.2 Health Check Failing

**Symptoms:**
*   Docker Compose `healthcheck` fails.
*   Kubernetes `livenessProbe` or `readinessProbe` fails, leading to pod restarts or traffic not being routed.

**Potential Causes:**
*   Application not listening on the expected port.
*   `/health` endpoint not implemented or returning non-200 status.
*   Application taking too long to start (initial delay too short).
*   Network issues preventing health check from reaching the application.

**Resolution Steps:**
1.  **Verify `/health` Endpoint:** Ensure the `/health` endpoint in `backend/app/main.py` is correctly implemented and returns a 200 OK status.
2.  **Check Application Logs:** See if the application is starting correctly and listening on port 8000.
3.  **Test Health Endpoint Manually:**
    *   From inside the container: `docker exec -it <container_name> curl -f http://localhost:8000/health`
    *   From the host (if port is exposed): `curl -f http://localhost:8000/health`
4.  **Adjust Probe Settings:** Increase `initialDelaySeconds`, `periodSeconds`, or `timeoutSeconds` in `docker-compose.prod.yml` or `k8s/backend-deployment.yaml` if the app takes longer to initialize.

### 4.3 Nginx Proxy Issues

**Symptoms:**
*   Cannot access the application via Nginx (e.g., `your-domain.com`).
*   Nginx returns 502 Bad Gateway or 504 Gateway Timeout.
*   HTTPS not working.

**Potential Causes:**
*   Nginx container not running.
*   Incorrect `nginx/nginx.conf` (e.g., wrong `proxy_pass` target, missing SSL certs).
*   Backend application not reachable from Nginx container.
*   Firewall blocking ports 80/443.

**Resolution Steps:**
1.  **Check Nginx Container Status and Logs:** `docker-compose logs nginx` or `kubectl logs <nginx-ingress-controller-pod>`. Look for configuration errors or upstream connection issues.
2.  **Verify `nginx.conf`:**
    *   Ensure `proxy_pass` points to the correct backend service name and port (`http://backend:8000`).
    *   Check SSL certificate paths and permissions if HTTPS is failing.
3.  **Test Backend Reachability from Nginx:**
    *   `docker exec -it <nginx-container> curl -f http://backend:8000/health`
    *   If using Kubernetes, ensure the Nginx Ingress Controller can reach the `backend-service`.
4.  **Check Firewall Rules:** Ensure ports 80 and 443 are open on the server/VM hosting Nginx.

### 4.4 Deployment Rollback

**Symptoms:**
*   A new deployment introduces critical bugs or performance regressions.

**Resolution Steps:**
1.  **Identify Previous Stable Version:**
    *   **Docker Compose:** Note the previous image tag or commit hash.
    *   **Kubernetes:** `kubectl rollout history deployment/backend-deployment`
2.  **Rollback:**
    *   **Docker Compose:** Manually update the image tag in `docker-compose.prod.yml` to the previous stable version and re-deploy:
        ```bash
        docker-compose -f docker-compose.prod.yml pull backend
        docker-compose -f docker-compose.prod.yml up -d --force-recreate backend
        ```
    *   **Kubernetes:**
        ```bash
        kubectl rollout undo deployment/backend-deployment # Rolls back to the previous revision
        # Or to a specific revision:
        # kubectl rollout undo deployment/backend-deployment --to-revision=<revision_number>
        ```
3.  **Verify Rollback:** Check application health and functionality after rollback.

---

## 5. Monitoring Issues

### 5.1 Metrics Not Appearing in Prometheus/Grafana

**Symptoms:**
*   Prometheus targets show `DOWN` status.
*   Grafana dashboards show "No data" or gaps.

**Potential Causes:**
*   Prometheus, Grafana, cAdvisor, or Node Exporter containers not running.
*   Incorrect `prometheus.yml` configuration (wrong target addresses/ports).
*   Firewall blocking Prometheus from scraping targets.
*   Application not exposing metrics (if applicable).

**Resolution Steps:**
1.  **Check Container Status:** `docker-compose ps` for all monitoring services.
2.  **Check Prometheus Targets:** Access Prometheus UI (`http://localhost:9090/targets`) and check the status of all configured targets.
3.  **Verify `prometheus.yml`:** Ensure `scrape_configs` have correct `targets` (e.g., `backend:8000`, `cadvisor:8080`, `node_exporter:9100`).
4.  **Check Network:** Ensure Prometheus container can reach the target containers on their respective ports.
5.  **Check Application Metrics Endpoint:** If your application exposes a `/metrics` endpoint, ensure it's accessible and returning valid Prometheus format.

### 5.2 Grafana Dashboard Empty/No Data

**Symptoms:**
*   Grafana dashboards load but display no data for panels.

**Potential Causes:**
*   Prometheus datasource not configured correctly in Grafana.
*   Prometheus not collecting data (see [5.1 Metrics Not Appearing](#51-metrics-not-appearing-in-prometheusgrafana)).
*   Dashboard queries are incorrect or refer to non-existent metrics.

**Resolution Steps:**
1.  **Check Grafana Datasource:** In Grafana UI, go to `Configuration -> Data sources` and ensure the Prometheus datasource is configured correctly and tests successfully.
2.  **Verify Prometheus Data:** Go to Prometheus UI (`http://localhost:9090/graph`) and manually query for the metrics expected by the Grafana dashboard. If metrics are not there, the issue is with Prometheus scraping.
3.  **Inspect Dashboard Queries:** Edit a problematic panel in Grafana and check its PromQL query. Ensure metric names and labels match what Prometheus is collecting.

---

## 6. CI/CD Issues

### 6.1 Pipeline Failure

**Symptoms:**
*   GitHub Actions workflow fails at a specific step.

**Potential Causes:**
*   Code quality issues (linting, formatting).
*   Security scan findings exceeding thresholds.
*   Test failures (unit, integration, performance).
*   Dependency installation issues.
*   Incorrect environment variables in CI/CD.

**Resolution Steps:**
1.  **Review Workflow Logs:** Click on the failed job/step in GitHub Actions to view detailed logs. The error message will usually pinpoint the exact cause.
2.  **Check Code Quality Reports:** If linting/formatting fails, review the output and fix code.
3.  **Analyze Test Reports:** If tests fail, review the pytest output to identify failing tests and their reasons.
4.  **Verify Environment Variables/Secrets:** Ensure all necessary environment variables and secrets are correctly configured in the GitHub Actions workflow.
5.  **Reproduce Locally:** If possible, try to run the failing step locally (e.g., `poetry run pytest`, `docker build`) to debug.

### 6.2 Image Build Failure

**Symptoms:**
*   `build_image` job fails in CI/CD.
*   Docker build command fails locally.

**Potential Causes:**
*   Syntax errors in `Dockerfile`.
*   Missing files or incorrect paths referenced in `Dockerfile`.
*   Dependency installation issues during the `builder` stage.
*   Insufficient build agent resources.

**Resolution Steps:**
1.  **Review Build Logs:** The Docker build output will show exactly where the build failed.
2.  **Check `Dockerfile`:** Carefully review the `Dockerfile` for typos, incorrect commands, or paths.
3.  **Verify `pyproject.toml`/`poetry.lock`:** Ensure dependencies are correctly defined and `poetry.lock` is up-to-date.
4.  **Build Locally:** Attempt to build the Docker image locally (`docker build -f backend/Dockerfile -t myimage .`) to get more immediate feedback and debug.
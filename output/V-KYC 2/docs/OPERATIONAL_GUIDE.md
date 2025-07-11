# Operational Guide: Troubleshooting, Runbook, Backup & Recovery, Performance

This document provides essential information for operating, maintaining, and troubleshooting the FastAPI and React full-stack application.

## Table of Contents

1.  [Troubleshooting Common Issues](#1-troubleshooting-common-issues)
2.  [Runbook Procedures](#2-runbook-procedures)
3.  [Backup and Recovery Procedures](#3-backup-and-recovery-procedures)
4.  [Performance Testing Strategy](#4-performance-testing-strategy)
5.  [Scalability Considerations](#5-scalability-considerations)

---

## 1. Troubleshooting Common Issues

This section covers common problems and their solutions.

### 1.1 Application Not Starting (Docker Compose)

**Symptoms:**
*   `docker compose up` fails or containers exit immediately.
*   `docker compose ps` shows containers with `Exit 1` or `unhealthy` status.

**Possible Causes & Solutions:**
*   **Port Conflicts:** Another process on your host is using a port required by the application (e.g., 80, 3000, 8000, 9090, 3001).
    *   **Solution:** Check port usage (`sudo lsof -i :<PORT>`) and stop conflicting processes or change ports in `docker-compose.dev.yml` / `docker-compose.prod.yml`.
*   **Missing Environment Variables:** `.env` file is missing or has incorrect values.
    *   **Solution:** Ensure `.env` exists and is correctly configured based on `.env.example`.
*   **Build Failures:** Docker image build failed.
    *   **Solution:** Run `docker compose build --no-cache` and inspect the build logs for errors.
*   **Application Errors:** The application itself has a startup error.
    *   **Solution:** Check container logs: `docker compose logs <service_name>`. Look for Python tracebacks (backend) or JavaScript errors (frontend).
*   **Health Check Failures:** The health check endpoint is not responding correctly.
    *   **Solution:** Verify the health check endpoint (`/health` for backend) is accessible and returns `200 OK`. Check application logs for errors related to health check.

### 1.2 Frontend Not Loading / Backend API Not Accessible

**Symptoms:**
*   Frontend shows blank page or network errors in browser console.
*   API requests from frontend fail (e.g., 404, 500, CORS errors).

**Possible Causes & Solutions:**
*   **Nginx Configuration:** Incorrect Nginx proxy pass or static file serving.
    *   **Solution:** Review `nginx/nginx.conf`. Ensure `proxy_pass` points to the correct internal Docker service name (e.g., `http://backend:8000`). Verify `root` path for static files.
*   **CORS Issues:** Frontend and backend are on different origins, and CORS headers are not correctly configured.
    *   **Solution:** In `backend/main.py`, ensure `CORSMiddleware` `allow_origins` includes the frontend's URL. In production, ensure `FRONTEND_URL` in `.env` is correct.
*   **Network Issues:** Docker containers cannot communicate.
    *   **Solution:** Verify all services are on the same Docker network (`app-network` in `docker-compose.prod.yml`). Check `docker compose logs` for network-related errors.
*   **Backend Down:** The backend service is not running or is unhealthy.
    *   **Solution:** Check `docker compose ps` for backend status. Check `docker compose logs backend`.

### 1.3 Monitoring Data Not Appearing (Prometheus/Grafana)

**Symptoms:**
*   Prometheus UI shows targets as `DOWN`.
*   Grafana dashboards show "No Data" or errors.

**Possible Causes & Solutions:**
*   **Prometheus Configuration:** Incorrect `prometheus.yml` scrape targets.
    *   **Solution:** Ensure `prometheus/prometheus.yml` correctly references service names (e.g., `backend:8000`, `node_exporter:9100`) within the Docker network.
*   **Service Not Exposing Metrics:** Backend or Node Exporter not exposing metrics correctly.
    *   **Solution:** For backend, ensure `prometheus_client` is correctly integrated and `/metrics` endpoint is accessible. For Node Exporter, ensure it's running.
*   **Grafana Data Source:** Grafana not configured to connect to Prometheus.
    *   **Solution:** Log into Grafana (`http://localhost:3001`), go to Configuration -> Data Sources, and ensure Prometheus is added and configured to point to `http://prometheus:9090`.

## 2. Runbook Procedures

This section outlines routine operational tasks and incident response steps.

### 2.1 Daily Checks

*   **Monitor Application Health:** Check Grafana dashboards for overall application health (request rates, error rates, latency).
*   **Check Container Status:** `docker compose -f docker-compose.prod.yml ps` to ensure all services are `Up` and `healthy`.
*   **Review Logs:** Periodically review logs for unusual patterns or errors: `docker compose -f docker-compose.prod.yml logs --tail 100`.

### 2.2 Deploying a New Version

1.  **Ensure CI/CD Passed:** Verify that the latest commit on `main` branch has successfully passed all CI/CD stages (build, test, scan).
2.  **Login to Deployment Server:** SSH into the production server.
3.  **Navigate to Application Directory:** `cd /path/to/your/app/on/server`
4.  **Pull Latest Images:**
    ```bash
    docker pull ghcr.io/your-org/your-repo/backend:latest
    docker pull ghcr.io/your-org/your-repo/frontend:latest
    ```
5.  **Update Environment Variables (if necessary):** Ensure the `.env` file on the server is up-to-date with any new or changed variables.
6.  **Perform Rolling Update (or downtime deployment):**
    *   **With Downtime (simpler):**
        ```bash
        docker compose -f docker-compose.prod.yml down --remove-orphans
        docker compose -f docker-compose.prod.yml up -d
        ```
    *   **Zero-Downtime (more complex, requires load balancer/orchestrator):** For Docker Compose, this typically involves external orchestration or careful manual steps. For this setup, a brief downtime is expected.
7.  **Verify Deployment:**
    *   Access the application URL in a browser.
    *   Check health endpoint: `curl -f http://localhost/health` (or via Nginx if configured).
    *   Check container logs: `docker compose -f docker-compose.prod.yml logs`.
    *   Monitor Grafana dashboards for new version performance.

### 2.3 Rolling Back a Deployment

If a new deployment introduces critical issues:

1.  **Identify Previous Stable Version:** Determine the SHA or tag of the last known good image.
2.  **Login to Deployment Server:** SSH into the production server.
3.  **Navigate to Application Directory:** `cd /path/to/your/app/on/server`
4.  **Pull Previous Images:**
    ```bash
    # Replace <PREVIOUS_SHA> with the actual commit SHA or tag
    docker pull ghcr.io/your-org/your-repo/backend:<PREVIOUS_SHA>
    docker pull ghcr.io/your-org/your-repo/frontend:<PREVIOUS_SHA>
    ```
5.  **Update Docker Compose (Temporarily):** Edit `docker-compose.prod.yml` to explicitly use the `<PREVIOUS_SHA>` tags for `backend` and `frontend` services.
6.  **Redeploy:**
    ```bash
    docker compose -f docker-compose.prod.yml down --remove-orphans
    docker compose -f docker-compose.prod.yml up -d
    ```
7.  **Verify Rollback:** Access the application and check logs/metrics to confirm stability.
8.  **Post-Rollback:** Investigate the cause of the failed deployment. Once fixed, redeploy the new version. Revert `docker-compose.prod.yml` to use `latest` tags or the new fixed SHA.

## 3. Backup and Recovery Procedures

This section outlines strategies for data backup and disaster recovery.

### 3.1 Data Backup Strategy

*   **Database (if applicable):**
    *   **Frequency:** Daily full backups, hourly incremental backups.
    *   **Method:** Use database-specific tools (e.g., `pg_dump` for PostgreSQL, `mysqldump` for MySQL).
    *   **Storage:** Store backups in a separate, highly durable storage service (e.g., AWS S3, Google Cloud Storage) with versioning enabled.
    *   **Encryption:** Encrypt backups at rest and in transit.
*   **Persistent Volumes (Docker Volumes):**
    *   **Frequency:** Daily snapshots or backups of Docker volumes (e.g., `prometheus_data`, `grafana_data`).
    *   **Method:** Use `docker cp` or a dedicated Docker volume backup tool/service.
    *   **Storage:** Same as database backups.
*   **Configuration Files:**
    *   All critical configuration files (`.env`, `nginx.conf`, `prometheus.yml`, `docker-compose.prod.yml`) are version-controlled in Git. This serves as a primary backup.

### 3.2 Disaster Recovery (DR) Plan

In case of a catastrophic failure (e.g., server loss, region outage):

1.  **Assess Impact:** Determine the scope of the outage and affected services.
2.  **Activate DR Environment (if applicable):** If a separate DR region/environment is configured, initiate its activation. For single-server deployments, this means provisioning a new server.
3.  **Provision New Infrastructure:**
    *   Use IaC (e.g., Terraform, CloudFormation) to provision a new server instance or cluster.
    *   Install Docker and necessary dependencies.
4.  **Clone Repository:** `git clone https://github.com/your-org/your-repo.git`
5.  **Restore Configuration:** Copy the latest `.env` file and any other non-versioned configurations to the new server.
6.  **Restore Data:**
    *   Restore the latest database backup to the new database instance.
    *   Restore persistent Docker volumes from backups.
7.  **Deploy Application:** Follow the "Deploying a New Version" procedure to deploy the application on the new infrastructure.
8.  **DNS Update:** Update DNS records to point to the new server's IP address or load balancer.
9.  **Verify Recovery:** Thoroughly test the application, check logs, and monitor metrics to ensure full functionality.
10. **Post-Recovery Review:** Conduct a post-mortem to identify root causes and improve the DR plan.

## 4. Performance Testing Strategy

Performance testing is crucial to ensure the application can handle expected load and identify bottlenecks.

*   **Tools:**
    *   **Locust:** (Python-based) Excellent for load testing APIs. Can simulate various user behaviors.
    *   **JMeter:** (Java-based) Comprehensive tool for various types of performance tests.
    *   **k6:** (JavaScript-based) Modern load testing tool with a focus on developer experience.
*   **Metrics to Monitor:**
    *   **Response Time:** Average, P95, P99 latency for key API endpoints.
    *   **Throughput:** Requests per second (RPS).
    *   **Error Rate:** Percentage of failed requests.
    *   **Resource Utilization:** CPU, Memory, Disk I/O, Network I/O on application servers and database.
    *   **Database Performance:** Query execution times, connection pool usage.
*   **Testing Scenarios:**
    *   **Load Test:** Gradually increase load to determine system behavior under expected peak conditions.
    *   **Stress Test:** Push the system beyond its normal operating capacity to find breaking points.
    *   **Soak Test (Endurance Test):** Run tests for an extended period to detect memory leaks or resource exhaustion.
*   **Integration with CI/CD:**
    *   Automate basic performance tests in CI/CD to catch regressions early.
    *   Set performance thresholds (e.g., max latency, min RPS) and fail the build if thresholds are exceeded.

## 5. Scalability Considerations

*   **Stateless Services:** Both FastAPI and React (once built) are designed to be stateless, allowing easy horizontal scaling.
*   **Load Balancing:** Nginx acts as a basic load balancer. For higher scale, consider cloud load balancers (e.g., AWS ALB, GCP Load Balancer) to distribute traffic across multiple instances of backend/frontend.
*   **Database Scaling:**
    *   Vertical scaling (more powerful server) is a short-term solution.
    *   Horizontal scaling (read replicas, sharding) for high read/write loads.
*   **Caching:** Implement caching layers (e.g., Redis, Memcached) for frequently accessed data to reduce database load.
*   **Message Queues:** For asynchronous tasks or high-volume event processing, integrate a message queue (e.g., RabbitMQ, Kafka, AWS SQS).
*   **Container Orchestration:** For complex deployments and advanced scaling, consider Kubernetes or AWS ECS/Fargate. Docker Compose is suitable for smaller deployments or as a local development tool.
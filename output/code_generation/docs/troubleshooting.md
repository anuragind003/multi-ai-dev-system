# Troubleshooting and Runbook

This document provides common troubleshooting steps and a runbook for operational issues encountered with the FastAPI Backend and Next.js Frontend application.

## Table of Contents

1.  [General Troubleshooting Steps](#1-general-troubleshooting-steps)
2.  [Common Issues and Solutions](#2-common-issues-and-solutions)
    *   [2.1. Application Not Accessible](#21-application-not-accessible)
    *   [2.2. Backend Not Responding / 500 Errors](#22-backend-not-responding--500-errors)
    *   [2.3. Frontend Not Loading / Blank Page](#23-frontend-not-loading--blank-page)
    *   [2.4. Database Connection Issues (Placeholder)](#24-database-connection-issues-placeholder)
    *   [2.5. CI/CD Pipeline Failures](#25-cicd-pipeline-failures)
    *   [2.6. Monitoring Stack Issues](#26-monitoring-stack-issues)
    *   [2.7. Performance Degradation](#27-performance-degradation)
3.  [Runbook Procedures](#3-runbook-procedures)
    *   [3.1. Restarting Services](#31-restarting-services)
    *   [3.2. Scaling Services](#32-scaling-services)
    *   [3.3. Rolling Back a Deployment](#33-rolling-back-a-deployment)
    *   [3.4. Checking Logs](#34-checking-logs)
    *   [3.5. Accessing Container Shell](#35-accessing-container-shell)
4.  [Escalation Matrix](#4-escalation-matrix)

---

## 1. General Troubleshooting Steps

Before diving into specific issues, follow these general steps:

1.  **Check Status:** Verify if all relevant services (backend, frontend, Nginx, Prometheus, Grafana) are running.
    *   **Docker Compose:** `docker compose ps` or `docker compose -f docker-compose.prod.yml ps`
    *   **Kubernetes:** `kubectl get pods -o wide`, `kubectl get deployments`, `kubectl get services`, `kubectl get ingress`
2.  **Check Logs:** Review logs for errors or unusual activity.
    *   **Docker Compose:** `docker compose logs <service_name>`
    *   **Kubernetes:** `kubectl logs <pod_name> -c <container_name>`
3.  **Check Connectivity:** Ensure network connectivity between services.
    *   From one container, try to `curl` another service's internal IP/hostname.
4.  **Check Resources:** Monitor CPU, memory, disk I/O, and network usage.
    *   **Docker Compose:** `docker stats`
    *   **Kubernetes:** `kubectl top pods`, `kubectl top nodes`
    *   **Grafana:** Check dashboards for resource utilization.
5.  **Check Health Endpoints:**
    *   Backend: `http://localhost:8000/health` (or via Nginx/Ingress)
    *   Frontend: `http://localhost:3000` (check if it loads)
6.  **Review Recent Changes:** Have there been any recent code deployments, configuration changes, or infrastructure updates? This is often the root cause.

## 2. Common Issues and Solutions

### 2.1. Application Not Accessible

**Symptoms:**
*   Browser shows "Site can't be reached" or "Connection refused".
*   Nginx/Ingress is not responding.

**Possible Causes:**
*   Nginx/Ingress container/pod is not running.
*   Port conflicts on the host machine.
*   Firewall blocking access.
*   Incorrect Nginx/Ingress configuration.

**Troubleshooting Steps:**
1.  **Verify Nginx/Ingress Status:**
    *   Docker Compose: `docker compose -f docker-compose.prod.yml ps nginx`
    *   Kubernetes: `kubectl get pods -l app=nginx-ingress-controller` (or similar label for your ingress controller)
2.  **Check Nginx Logs:** `docker compose -f docker-compose.prod.yml logs nginx` or `kubectl logs <nginx-ingress-pod>`
3.  **Check Nginx Configuration:** Ensure `nginx/nginx.conf` has correct `listen` directives and `server_name`.
4.  **Check Host Firewall:** Ensure ports 80/443 are open on the host machine.
5.  **Kubernetes Specific:**
    *   Verify Ingress Controller is running and healthy.
    *   Check Ingress events: `kubectl describe ingress app-ingress`
    *   Ensure DNS is correctly pointing to the Ingress Controller's external IP.

### 2.2. Backend Not Responding / 500 Errors

**Symptoms:**
*   Frontend displays "Error fetching from backend".
*   API calls return 500 Internal Server Error.
*   Backend health check (`/health`) fails.

**Possible Causes:**
*   Backend container/pod crashed or is not running.
*   Application error in FastAPI.
*   Incorrect environment variables.
*   Database connection issues (if applicable).

**Troubleshooting Steps:**
1.  **Verify Backend Status:**
    *   Docker Compose: `docker compose ps backend`
    *   Kubernetes: `kubectl get pods -l app=fastapi-backend`
2.  **Check Backend Logs:** `docker compose logs backend` or `kubectl logs <backend-pod>` for Python tracebacks.
3.  **Check Health Endpoint:** Directly access `http://localhost:8000/health` (if port is exposed) or `http://backend-service:8000/health` from another container/pod.
4.  **Check Environment Variables:** Ensure `SECRET_KEY` and other critical variables are correctly set in `.env` or Kubernetes Secrets.
5.  **Resource Exhaustion:** Check Grafana dashboard for backend CPU/Memory usage. If consistently high, consider scaling up or optimizing code.
6.  **Database Connectivity:** (If applicable) Check backend logs for database connection errors.

### 2.3. Frontend Not Loading / Blank Page

**Symptoms:**
*   Browser shows a blank page or JavaScript errors in the console.
*   Frontend container/pod is running but not serving content.

**Possible Causes:**
*   Frontend container/pod crashed or is not running.
*   Build issues (Next.js build failed).
*   Incorrect `NEXT_PUBLIC_API_BASE_URL`.
*   JavaScript runtime errors.

**Troubleshooting Steps:**
1.  **Verify Frontend Status:**
    *   Docker Compose: `docker compose ps frontend`
    *   Kubernetes: `kubectl get pods -l app=nextjs-frontend`
2.  **Check Frontend Logs:** `docker compose logs frontend` or `kubectl logs <frontend-pod>` for Next.js errors.
3.  **Check Browser Console:** Look for JavaScript errors or network request failures (e.g., to the backend API).
4.  **Verify `NEXT_PUBLIC_API_BASE_URL`:** Ensure it points to the correct backend service address (e.g., `http://backend:8000` in Docker Compose, `http://backend-service:8000` in Kubernetes).
5.  **Rebuild Frontend:** If recent code changes, try rebuilding the frontend image.

### 2.4. Database Connection Issues (Placeholder)

**Symptoms:**
*   Backend logs show database connection errors.
*   Application features requiring database access fail.

**Possible Causes:**
*   Database server is down or unreachable.
*   Incorrect database credentials or connection string.
*   Database full or resource exhaustion.

**Troubleshooting Steps:**
1.  **Verify Database Status:** Check if the database container/VM is running.
2.  **Check Database Logs:** Review database server logs for errors.
3.  **Test Connectivity:** From the backend container/pod, try to ping or connect to the database host/port.
4.  **Verify Credentials:** Double-check database username, password, host, and port in backend environment variables.
5.  **Check Database Resources:** Monitor database server CPU, memory, disk space.

### 2.5. CI/CD Pipeline Failures

**Symptoms:**
*   GitHub Actions workflow fails at a specific stage (lint, test, build, deploy).

**Possible Causes:**
*   Code quality issues (linting/formatting errors).
*   Test failures (unit, integration, E2E).
*   Docker build errors.
*   Vulnerability scan findings.
*   Deployment errors (Kubernetes manifests, cluster connectivity, secrets).
*   Incorrect GitHub Secrets.

**Troubleshooting Steps:**
1.  **Review Workflow Logs:** Go to the GitHub Actions tab in your repository, click on the failed workflow run, and examine the logs for the failing step.
2.  **Reproduce Locally:** If a test or build step fails, try to reproduce the issue locally (e.g., `poetry run pytest`, `yarn cypress run`, `docker build`).
3.  **Check Secrets:** Ensure all required GitHub Secrets are correctly configured and not expired.
4.  **Kubernetes Deployment Failures:**
    *   Check `kubectl get events` in the target namespace.
    *   Check `kubectl describe pod <pod-name>` for deployment errors.
    *   Verify `KUBECONFIG_BASE64` secret is valid.

### 2.6. Monitoring Stack Issues

**Symptoms:**
*   Prometheus UI not accessible or showing "0 targets up".
*   Grafana dashboards are empty or show "No Data".

**Possible Causes:**
*   Prometheus/Grafana containers/pods not running.
*   Incorrect Prometheus configuration (`prometheus.yml`).
*   Prometheus unable to scrape targets (firewall, incorrect service name/port).
*   Grafana unable to connect to Prometheus datasource.

**Troubleshooting Steps:**
1.  **Verify Service Status:** `docker compose ps prometheus grafana` or `kubectl get pods -l app=prometheus`, `kubectl get pods -l app=grafana`.
2.  **Check Logs:** `docker compose logs prometheus` and `docker compose logs grafana`.
3.  **Prometheus Configuration:**
    *   Access Prometheus UI (`http://localhost:9090`).
    *   Go to `Status -> Targets` to see if `fastapi-backend` target is up. If not, check the `backend:8000` address in `prometheus.yml`.
    *   Go to `Status -> Configuration` to verify the loaded config.
4.  **Grafana Datasource:**
    *   Log into Grafana (`http://localhost:3001`).
    *   Go to `Connections -> Data sources` and ensure the Prometheus datasource is healthy. Edit it to verify the URL (`http://prometheus:9090`).

### 2.7. Performance Degradation

**Symptoms:**
*   Application feels slow.
*   High latency reported by monitoring.
*   High CPU/Memory usage.

**Possible Causes:**
*   Insufficient resources (CPU, Memory) allocated to containers/pods.
*   Application bottlenecks (inefficient code, N+1 queries).
*   Database performance issues.
*   Increased traffic.

**Troubleshooting Steps:**
1.  **Monitor Metrics:** Use Grafana dashboards to identify which component is bottlenecking (backend CPU, database query latency, network I/O).
2.  **Resource Scaling:**
    *   Docker Compose: Increase `resources` limits/requests in `docker-compose.prod.yml` or scale up the host VM.
    *   Kubernetes: Adjust `replicas` in deployments, increase `resources` limits/requests, or scale up cluster nodes.
3.  **Performance Testing:** Run Locust tests to simulate load and identify specific bottlenecks.
4.  **Code Profiling:** Use language-specific profiling tools (e.g., `cProfile` for Python, Node.js profiler) to pinpoint slow code paths.
5.  **Database Optimization:** Analyze slow queries, add indexes, optimize schema.

## 3. Runbook Procedures

### 3.1. Restarting Services

*   **Docker Compose:**
    ```bash
    docker compose -f docker-compose.prod.yml restart <service_name> # e.g., backend, frontend, nginx
    # Or restart all:
    docker compose -f docker-compose.prod.yml restart
    ```
*   **Kubernetes:**
    ```bash
    # Rolling restart a deployment (recommended)
    kubectl rollout restart deployment/<deployment_name> # e.g., backend-deployment, frontend-deployment
    # Force delete a pod (will be recreated by deployment)
    kubectl delete pod <pod_name>
    ```

### 3.2. Scaling Services

*   **Docker Compose:**
    ```bash
    docker compose -f docker-compose.prod.yml up -d --scale backend=4 # Scale backend to 4 instances
    ```
*   **Kubernetes:**
    ```bash
    kubectl scale deployment/<deployment_name> --replicas=<number> # e.g., kubectl scale deployment/backend-deployment --replicas=3
    ```

### 3.3. Rolling Back a Deployment

*   **Kubernetes:**
    ```bash
    # Check deployment history
    kubectl rollout history deployment/<deployment_name>
    # Rollback to previous revision
    kubectl rollout undo deployment/<deployment_name>
    # Rollback to a specific revision
    kubectl rollout undo deployment/<deployment_name> --to-revision=<revision_number>
    ```

### 3.4. Checking Logs

*   **Docker Compose:**
    ```bash
    docker compose logs <service_name> # View logs for a service
    docker compose logs -f <service_name> # Follow logs
    docker compose logs --tail 100 <service_name> # Last 100 lines
    ```
*   **Kubernetes:**
    ```bash
    kubectl logs <pod_name> # Logs for a specific pod
    kubectl logs -f <pod_name> # Follow logs
    kubectl logs --tail 100 <pod_name> # Last 100 lines
    kubectl logs <pod_name> -c <container_name> # If multiple containers in pod
    ```

### 3.5. Accessing Container Shell

*   **Docker Compose:**
    ```bash
    docker compose exec <service_name> sh # or bash, if available
    ```
*   **Kubernetes:**
    ```bash
    kubectl exec -it <pod_name> -- sh # or bash, if available
    ```

## 4. Escalation Matrix

If the issue cannot be resolved using the steps above, escalate to the appropriate team/individual:

| Severity | Description                                   | Primary Contact | Secondary Contact |
| :------- | :-------------------------------------------- | :-------------- | :---------------- |
| **P1**   | Critical outage, application completely down  | On-Call DevOps  | Lead Developer    |
| **P2**   | Major functionality impaired, severe degradation | DevOps Team     | Senior Developer  |
| **P3**   | Minor issue, workaround available             | Developer Team  | QA Lead           |
| **P4**   | Cosmetic or low-impact issue                  | Support Team    |                   |

**Contact Information:**
*   **On-Call DevOps:** [Phone Number/PagerDuty Link]
*   **DevOps Team:** [Email/Slack Channel]
*   **Lead Developer:** [Email/Slack Handle]
*   **Developer Team:** [Email/Slack Channel]
*   **QA Lead:** [Email/Slack Handle]
*   **Support Team:** [Email/Ticketing System]

---
*This runbook is a living document. Please contribute to its improvement.*
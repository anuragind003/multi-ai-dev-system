# Troubleshooting Guide and Runbook for FastAPI Redis App

This document provides guidance for common issues, debugging steps, and runbook procedures for the FastAPI application with Redis.

## Table of Contents

1.  [General Troubleshooting Steps](#general-troubleshooting-steps)
2.  [Common Issues and Solutions](#common-issues-and-solutions)
    *   [Application Not Starting / Connection Refused](#application-not-starting--connection-refused)
    *   [Redis Connection Issues](#redis-connection-issues)
    *   [High Latency / Slow Responses](#high-latency--slow-responses)
    *   [High CPU / Memory Usage](#high-cpu--memory-usage)
    *   [Cache Invalidation Issues](#cache-invalidation-issues)
    *   [Session Management Problems](#session-management-problems)
    *   [Prometheus Not Scraping Metrics](#prometheus-not-scraping-metrics)
    *   [Deployment Failures](#deployment-failures)
3.  [Runbook Procedures](#runbook-procedures)
    *   [Redis Service Down](#redis-service-down)
    *   [Application Pod/Container CrashLoopBackOff](#application-podcontainer-crashloopbackoff)
    *   [High Error Rate Alert](#high-error-rate-alert)
    *   [Disk Full Alert (Redis Persistence)](#disk-full-alert-redis-persistence)
4.  [Debugging Tools and Commands](#debugging-tools-and-commands)
    *   [Docker Commands](#docker-commands)
    *   [Redis CLI Commands](#redis-cli-commands)
    *   [Kubernetes Commands (if applicable)](#kubernetes-commands-if-applicable)
    *   [Monitoring Tools](#monitoring-tools)

---

## 1. General Troubleshooting Steps

Before diving into specific issues, follow these general steps:

1.  **Check Logs:** Always start by checking the logs of the affected service (FastAPI app, Redis, Nginx, Prometheus).
    *   `docker-compose logs <service_name>` (for local Docker Compose)
    *   `kubectl logs <pod_name>` (for Kubernetes)
    *   Check cloud provider logs (CloudWatch, Stackdriver, etc.).
2.  **Verify Service Status:** Ensure all dependent services are running.
    *   `docker-compose ps`
    *   `kubectl get pods`
3.  **Check Network Connectivity:** Ensure services can communicate with each other (e.g., app to Redis, Nginx to app).
    *   `ping <hostname>`
    *   `telnet <hostname> <port>`
    *   `nc -vz <hostname> <port>`
4.  **Review Configuration:** Double-check environment variables, `.env` files, and configuration files (`nginx.conf`, `prometheus.yml`).
5.  **Restart Service:** A simple restart can often resolve transient issues.
    *   `docker-compose restart <service_name>`
    *   `kubectl rollout restart deployment <deployment_name>`
6.  **Check Resource Utilization:** Monitor CPU, memory, and disk I/O.
    *   `docker stats`
    *   `kubectl top pods`
    *   Prometheus/Grafana dashboards.

---

## 2. Common Issues and Solutions

### Application Not Starting / Connection Refused

*   **Symptom:** `Connection refused` errors when trying to access the app, or app container exits immediately.
*   **Possible Causes:**
    *   Port conflict.
    *   Application code error during startup.
    *   Incorrect `CMD` in Dockerfile or `command` in Docker Compose.
    *   Dependency not ready (e.g., Redis not started yet).
*   **Solution:**
    1.  Check app container logs (`docker-compose logs app`). Look for Python tracebacks.
    2.  Verify port mapping in `docker-compose.yml` (e.g., `8000:8000`).
    3.  Ensure no other process is using port 8000 on your host (`sudo lsof -i :8000`).
    4.  If using `docker-compose`, ensure `depends_on` is correctly configured and services are healthy.
    5.  For production, ensure Gunicorn/Uvicorn workers are configured correctly and have enough resources.

### Redis Connection Issues

*   **Symptom:** Application logs show `redis.exceptions.ConnectionError` or `Redis connection not available.`
*   **Possible Causes:**
    *   Redis service not running.
    *   Incorrect `REDIS_HOST`, `REDIS_PORT`, or `REDIS_PASSWORD` in `.env` or environment variables.
    *   Network connectivity issues between app and Redis.
    *   Redis password mismatch.
    *   Redis max connections limit reached.
*   **Solution:**
    1.  Check Redis container logs (`docker-compose logs redis`).
    2.  Verify Redis service status (`docker-compose ps redis`).
    3.  Confirm `REDIS_HOST` (e.g., `redis` for Docker Compose, or the correct ElastiCache endpoint) and `REDIS_PORT` are correct.
    4.  Use `redis-cli` to test connectivity and authentication:
        ```bash
        docker-compose exec redis redis-cli -a <your_redis_password> PING
        # Or if Redis is on host: redis-cli -h <host> -p <port> -a <password> PING
        ```
    5.  Check security group rules (for AWS ElastiCache) or firewall rules to ensure app can reach Redis on port 6379.

### High Latency / Slow Responses

*   **Symptom:** API requests take a long time to respond.
*   **Possible Causes:**
    *   Application code inefficiencies (e.g., blocking I/O, complex database queries).
    *   Redis performance bottleneck (e.g., slow commands, high memory usage leading to swapping, network latency).
    *   Insufficient resources (CPU, memory) for app or Redis.
    *   Network congestion.
*   **Solution:**
    1.  **Monitor:** Use Prometheus/Grafana to check:
        *   Application request duration metrics.
        *   Redis metrics: `redis_commands_total`, `redis_memory_used_bytes`, `redis_cpu_usage_total`, `redis_connected_clients`.
    2.  **Profile Application:** Use Python profiling tools to identify bottlenecks in your FastAPI code.
    3.  **Optimize Redis Usage:**
        *   Avoid `KEYS` command in production. Use `SCAN`.
        *   Batch commands using pipelines.
        *   Ensure data structures are used efficiently.
        *   Check for large keys.
    4.  **Scale:**
        *   Increase FastAPI app workers (Gunicorn `--workers`).
        *   Upgrade Redis instance type (ElastiCache) or allocate more resources to Docker container.
        *   Consider Redis clustering for horizontal scaling.

### High CPU / Memory Usage

*   **Symptom:** Application or Redis containers consume excessive CPU/memory.
*   **Possible Causes:**
    *   **App:** Memory leaks, inefficient loops, large data processing.
    *   **Redis:** Large dataset, high number of connections, inefficient commands, AOF/RDB persistence operations.
*   **Solution:**
    1.  **Monitor:** Use `docker stats`, `kubectl top`, and Grafana dashboards.
    2.  **App:**
        *   Review recent code changes for potential memory leaks.
        *   Optimize data structures and algorithms.
        *   Adjust Gunicorn worker count.
    3.  **Redis:**
        *   Check `redis_memory_used_bytes` and `redis_used_memory_peak`.
        *   Analyze Redis `INFO` output (especially `memory` section).
        *   Consider setting `maxmemory` and `maxmemory-policy` to prevent OOM.
        *   If using AOF, ensure `appendfsync` is not set to `always` for high write loads.
        *   Upgrade Redis instance type.

### Cache Invalidation Issues

*   **Symptom:** Stale data being served from cache, or data not appearing in cache when expected.
*   **Possible Causes:**
    *   Incorrect TTL (Time-To-Live) values.
    *   Application logic not invalidating cache correctly after data updates.
    *   Race conditions.
*   **Solution:**
    1.  **Verify TTLs:** Check `TTL` on keys in Redis using `redis-cli TTL <key>`.
    2.  **Review Invalidation Logic:** Ensure that whenever underlying data changes, the corresponding cache entries are either updated or deleted.
    3.  **Consistency Model:** Understand the consistency model of your caching strategy (e.g., eventual consistency vs. strong consistency).
    4.  **Monitor Cache Hit/Miss Ratio:** Use custom metrics to track how often cache hits occur.

### Session Management Problems

*   **Symptom:** Users losing sessions, unexpected logouts, or session data not persisting.
*   **Possible Causes:**
    *   Session ID not being set/read correctly from cookies.
    *   Redis session data expiring prematurely (`SESSION_TTL`).
    *   Redis connection issues.
    *   Load balancer not sticky sessions (if applicable).
*   **Solution:**
    1.  **Check Cookies:** Inspect browser cookies for `session_id`.
    2.  **Verify Redis:** Check if session keys exist in Redis (`redis-cli KEYS "session:*"`) and their TTLs (`TTL session:<id>`).
    3.  **Review Session Logic:** Ensure `set_cookie` and `delete_cookie` are correctly implemented with `httponly`, `secure`, and `max_age` attributes.
    4.  **Load Balancer:** If using multiple app instances behind a load balancer, ensure sticky sessions are enabled if your session management requires it (though Redis-backed sessions are generally stateless from the app's perspective).

### Prometheus Not Scraping Metrics

*   **Symptom:** No data for FastAPI or Redis Exporter in Prometheus UI.
*   **Possible Causes:**
    *   Incorrect `targets` in `prometheus.yml`.
    *   Firewall blocking Prometheus from reaching targets.
    *   Metrics endpoint (`/metrics`) not exposed or returning errors.
    *   Redis Exporter not running or misconfigured.
*   **Solution:**
    1.  **Check Prometheus UI:** Go to `http://localhost:9090/targets` and check the status of `fastapi-app` and `redis-exporter` jobs. Look for `UP` status.
    2.  **Verify Connectivity:** From inside the Prometheus container, try to `curl` the metrics endpoints:
        ```bash
        docker-compose exec prometheus curl http://app:8000/metrics
        docker-compose exec prometheus curl http://redis_exporter:9121/metrics
        ```
    3.  **Review `prometheus.yml`:** Ensure `metrics_path` and `targets` are correct.
    4.  **Check Firewalls/Security Groups:** Ensure Prometheus can reach the application and Redis Exporter ports.

### Deployment Failures

*   **Symptom:** CI/CD pipeline fails at the deployment stage.
*   **Possible Causes:**
    *   Incorrect cloud credentials.
    *   Insufficient IAM permissions.
    *   Infrastructure limits reached.
    *   Misconfigured deployment script/Terraform.
*   **Solution:**
    1.  **Check CI/CD Logs:** Review the detailed logs of the failed deployment step in GitHub Actions.
    2.  **Verify Credentials:** Ensure `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, etc., are correctly set as GitHub Secrets and have the necessary permissions.
    3.  **Test Locally:** If possible, try to run the deployment command/Terraform apply locally with the same credentials to reproduce the error.
    4.  **Cloud Provider Console:** Check the cloud provider's console for specific error messages (e.g., CloudFormation events, ECS service events, Kubernetes events).

---

## 3. Runbook Procedures

### Redis Service Down

**Alert:** `RedisDown` (or similar from Prometheus/Grafana)

**Severity:** Critical

**Impact:** Application will not be able to cache data or manage sessions, leading to degraded performance or functionality.

**Procedure:**

1.  **Verify Alert:**
    *   Confirm Redis is truly down by checking its container status (`docker-compose ps redis` or `kubectl get pods -l app=redis`).
    *   Attempt to `PING` Redis using `redis-cli`.
2.  **Check Logs:**
    *   Examine Redis container logs for recent errors or shutdown messages (`docker-compose logs redis`).
    *   Check system logs for host-level issues (e.g., OOM killer, disk full).
3.  **Attempt Restart:**
    *   `docker-compose restart redis` (for Docker Compose)
    *   `kubectl rollout restart deployment redis` (for Kubernetes)
4.  **Monitor Restart:** Observe logs and status to ensure Redis comes back up.
5.  **If Restart Fails:**
    *   **Disk Space:** Check if the volume mounted for Redis data is full. If so, clear space or resize the volume.
    *   **Configuration:** Review `redis.conf` (or Docker Compose command) for any recent changes that might prevent startup.
    *   **Resource Limits:** Ensure the container/VM has enough memory and CPU.
    *   **Data Corruption:** If logs indicate data corruption, you might need to restore from a backup (see [Backup and Recovery](#backup-and-recovery)). **WARNING: This will cause data loss since the last backup.**
6.  **Escalate:** If Redis cannot be brought back online after these steps, escalate to the infrastructure team.

### Application Pod/Container CrashLoopBackOff

**Alert:** `AppCrashLoopBackOff` (or similar from Kubernetes/Docker)

**Severity:** High

**Impact:** Application is unavailable, leading to service outage.

**Procedure:**

1.  **Verify Alert:**
    *   Confirm the application container/pod is in a `CrashLoopBackOff` state (`docker-compose ps app` or `kubectl get pods`).
2.  **Check Logs:**
    *   Immediately check the logs of the crashing container:
        *   `docker-compose logs app`
        *   `kubectl logs <pod_name> -f` (for live logs)
        *   `kubectl logs <pod_name> --previous` (for logs from the previous crash)
    *   Look for Python tracebacks, `ModuleNotFoundError`, `ConnectionError` to dependencies, or configuration errors.
3.  **Review Recent Changes:**
    *   Was a new code version deployed?
    *   Were environment variables changed?
    *   Was a new Docker image built?
4.  **Dependency Check:**
    *   Is Redis running and accessible? (See [Redis Service Down](#redis-service-down))
    *   Are other external services (databases, APIs) reachable?
5.  **Configuration Check:**
    *   Verify `.env` variables are correct and complete.
    *   Check `Dockerfile` and `docker-compose.prod.yml` for any recent changes.
6.  **Rollback (if recent deployment):**
    *   If a new deployment caused the issue, rollback to the previous stable version.
        *   `kubectl rollout undo deployment <deployment_name>` (for Kubernetes)
        *   Revert the CI/CD trigger (e.g., revert Git commit on `main` branch).
7.  **Debug in Dev Environment:** If the issue is not immediately obvious, try to reproduce it in a development environment with the same code and configuration.
8.  **Escalate:** If the issue persists after rollback and basic debugging, escalate to the development or infrastructure team.

### High Error Rate Alert

**Alert:** `AppHighErrorRate` (e.g., HTTP 5xx errors > 5% for 5 minutes)

**Severity:** Medium to High

**Impact:** Users are experiencing failures, service quality is degraded.

**Procedure:**

1.  **Verify Alert:**
    *   Check Grafana dashboards for the application's error rate.
    *   Confirm the specific endpoints or types of errors.
2.  **Check Logs:**
    *   Filter application logs for error messages (e.g., `ERROR`, `500`).
    *   Look for recurring patterns, specific endpoints, or user IDs.
3.  **Identify Root Cause:**
    *   **Dependency Issues:** Are errors related to Redis, database, or external API calls? Check their respective health and logs.
    *   **Resource Exhaustion:** Is the application running out of CPU, memory, or file descriptors? Check `docker stats` or `kubectl top`.
    *   **Bad Deployment:** Was there a recent deployment that introduced a bug?
    *   **Traffic Spike:** Is there an unusual increase in traffic causing overload?
4.  **Mitigation:**
    *   **Scale Up:** Temporarily increase application instances/workers.
    *   **Rate Limiting:** If due to traffic spike, ensure Nginx rate limiting is effective.
    *   **Rollback:** If a recent deployment is suspected, perform a rollback.
5.  **Deep Dive:** If the cause is not immediately apparent, involve the development team for code-level debugging.

### Disk Full Alert (Redis Persistence)

**Alert:** `RedisDiskFull` (or similar from host monitoring)

**Severity:** High

**Impact:** Redis may stop saving data, leading to data loss on restart, or the host system may become unstable.

**Procedure:**

1.  **Verify Alert:**
    *   Confirm disk usage on the volume where Redis persists data (`df -h`).
    *   Check Redis logs for "disk full" errors.
2.  **Identify Culprit:**
    *   Is it the Redis data (`dump.rdb` or `appendonly.aof`) that's consuming space?
    *   Are there other large files on the same volume (e.g., old logs, other application data)?
3.  **Immediate Action (if Redis data is the cause):**
    *   **Temporary Solution:** If possible, temporarily disable AOF or RDB persistence (requires Redis restart and carries data loss risk). **This is a last resort.**
    *   **Clear Old Backups:** If backups are stored on the same volume, move or delete old ones.
4.  **Long-Term Solution:**
    *   **Resize Volume:** Increase the size of the disk volume.
    *   **Optimize Redis Data:**
        *   Review Redis usage patterns. Are there very large keys?
        *   Implement data eviction policies (`maxmemory`, `maxmemory-policy`).
        *   Consider sharding data across multiple Redis instances.
    *   **Separate Volumes:** Ensure Redis persistence data is on a dedicated volume.
    *   **Automate Cleanup:** Implement automated cleanup for old logs or temporary files.
5.  **Escalate:** If immediate action is not possible or the issue recurs, escalate to the infrastructure team.

---

## 4. Debugging Tools and Commands

### Docker Commands

*   `docker ps`: List running containers.
*   `docker logs <container_id_or_name>`: View container logs. Add `-f` for follow, `--tail N` for last N lines.
*   `docker exec -it <container_id_or_name> bash`: Get a shell inside a running container.
*   `docker inspect <container_id_or_name>`: Get detailed information about a container (IP address, volumes, etc.).
*   `docker stats`: Live stream of container resource usage (CPU, memory, network I/O).
*   `docker-compose up`: Start services defined in `docker-compose.yml`.
*   `docker-compose down`: Stop and remove services.
*   `docker-compose restart <service_name>`: Restart a specific service.
*   `docker-compose logs <service_name>`: View logs for a service.

### Redis CLI Commands

*   `redis-cli -h <host> -p <port> -a <password> PING`: Test connectivity.
*   `redis-cli -h <host> -p <port> -a <password> INFO`: Get detailed information about Redis server (memory, clients, persistence, etc.).
*   `redis-cli -h <host> -p <port> -a <password> GET <key>`: Retrieve a value.
*   `redis-cli -h <host> -p <port> -a <password> TTL <key>`: Get time-to-live for a key.
*   `redis-cli -h <host> -p <port> -a <password> KEYS "*"`: **WARNING: Do not use in production on large datasets.** Lists all keys. Use `SCAN` for production.
*   `redis-cli -h <host> -p <port> -a <password> MONITOR`: See all commands processed by the Redis server in real-time.

### Kubernetes Commands (if applicable)

*   `kubectl get pods`: List pods.
*   `kubectl describe pod <pod_name>`: Get detailed information about a pod, including events.
*   `kubectl logs <pod_name>`: View pod logs.
*   `kubectl exec -it <pod_name> -- bash`: Get a shell inside a pod.
*   `kubectl top pod <pod_name>`: Show resource usage for a pod.
*   `kubectl rollout status deployment <deployment_name>`: Check deployment status.
*   `kubectl rollout restart deployment <deployment_name>`: Restart a deployment.
*   `kubectl rollout undo deployment <deployment_name>`: Rollback to previous deployment.
*   `kubectl get events`: View cluster events.

### Monitoring Tools

*   **Prometheus UI:** `http://localhost:9090` (or your Prometheus URL). Use the Graph explorer to query metrics.
*   **Grafana:** Your Grafana URL. Use dashboards to visualize trends and identify anomalies.
*   **Cloud Provider Monitoring:** AWS CloudWatch, Azure Monitor, Google Cloud Monitoring for infrastructure metrics and logs.

---
# Operational Guide for FastAPI Monolithic Application

This document provides essential information for operating, maintaining, and troubleshooting the FastAPI monolithic application.

## Table of Contents

1.  [Backup and Recovery Procedures](#1-backup-and-recovery-procedures)
    *   [Database Backup (PostgreSQL)](#database-backup-postgresql)
    *   [Application Configuration Backup](#application-configuration-backup)
    *   [Recovery Procedures](#recovery-procedures)
2.  [Troubleshooting Guide](#2-troubleshooting-guide)
    *   [General Troubleshooting Steps](#general-troubleshooting-steps)
    *   [Common Issues and Solutions](#common-issues-and-solutions)
        *   [Application Not Responding (5xx Errors)](#application-not-responding-5xx-errors)
        *   [Database Connection Issues](#database-connection-issues)
        *   [High CPU/Memory Usage](#high-cpumemory-usage)
        *   [Slow API Responses](#slow-api-responses)
        *   [Deployment Failures](#deployment-failures)
        *   [Monitoring Data Missing](#monitoring-data-missing)
3.  [Runbook](#3-runbook)
    *   [Deployment Rollback](#deployment-rollback)
    *   [Restarting Services](#restarting-services)
    *   [Scaling Up/Down](#scaling-updown)
    *   [Incident Response Checklist](#incident-response-checklist)

---

## 1. Backup and Recovery Procedures

Regular backups are crucial for disaster recovery.

### Database Backup (PostgreSQL)

Assuming PostgreSQL is running in a Docker container or on an RDS instance.

**Method 1: Using `pg_dump` (for Dockerized PostgreSQL)**

1.  **Identify the database container:**
    ```bash
    docker ps -f "name=db" # Or whatever your DB service name is
    ```
    Note the container ID or name (e.g., `your-app-db-1`).

2.  **Perform a full database dump:**
    ```bash
    docker exec -t <db_container_id_or_name> pg_dumpall -U $POSTGRES_USER > backup_$(date +%Y%m%d_%H%M%S).sql
    ```
    Replace `$POSTGRES_USER` with your actual PostgreSQL username (e.g., `produser`).
    *   **Automation:** Schedule this command using `cron` on a dedicated backup server or a CI/CD job.
    *   **Storage:** Store backups in a secure, off-site location (e.g., AWS S3, Google Cloud Storage) with versioning and lifecycle policies.

**Method 2: AWS RDS Snapshots (if using RDS)**

*   **Automated Snapshots:** RDS automatically creates and retains daily snapshots. Configure the retention period (e.g., 7-35 days) in the RDS console.
*   **Manual Snapshots:** You can create manual snapshots for specific points in time (e.g., before a major deployment).
    *   Go to RDS console -> Databases -> Select your DB instance -> Actions -> Take snapshot.
*   **Point-in-Time Recovery:** RDS allows restoring to any point within your backup retention period (requires automated backups to be enabled).

### Application Configuration Backup

*   **Version Control:** All critical application configurations (`.env.prod`, Nginx configs, Prometheus/Grafana configs, Terraform files) are stored in this Git repository. Git serves as the primary backup for these files.
*   **Secrets Management:** Sensitive environment variables (e.g., `DB_PASSWORD`) should be managed by a dedicated secrets manager (AWS Secrets Manager, HashiCorp Vault) and not directly committed to Git. Ensure your secrets manager has its own backup/replication strategy.

### Recovery Procedures

**1. Database Recovery:**

*   **From `pg_dump` backup:**
    1.  **Restore to a new/empty database:**
        ```bash
        docker exec -i <new_db_container_id_or_name> psql -U $POSTGRES_USER < backup_file.sql
        ```
    2.  **Alternatively, drop and recreate database, then restore:**
        ```bash
        docker exec -t <db_container_id_or_name> psql -U $POSTGRES_USER -c "DROP DATABASE IF EXISTS proddb;"
        docker exec -t <db_container_id_or_name> psql -U $POSTGRES_USER -c "CREATE DATABASE proddb;"
        docker exec -i <db_container_id_or_name> psql -U $POSTGRES_USER -d proddb < backup_file.sql
        ```
*   **From AWS RDS Snapshot:**
    1.  Go to RDS console -> Snapshots.
    2.  Select the desired snapshot -> Actions -> Restore snapshot.
    3.  You can restore to a new DB instance or overwrite an existing one (use caution).

**2. Application Server Recovery (EC2 Instance):**

*   **If instance is corrupted/lost:**
    1.  **Provision a new EC2 instance:** Use Terraform (`terraform apply`) to provision a new instance with the latest AMI and user data.
    2.  **Deploy the application:** Run the CI/CD deployment step to pull the latest Docker image and start the services.
    3.  **DNS Update:** If the new instance has a different IP, update your DNS records (e.g., Route 53) to point to the new instance's IP or use a Load Balancer.

**3. Full System Recovery (Disaster Recovery):**

In a catastrophic event (e.g., entire AWS region outage):

1.  **Provision Infrastructure in a New Region:** Use Terraform to deploy the entire infrastructure (VPC, subnets, EC2, RDS) in a different AWS region. Ensure your Terraform state is backed up (e.g., in S3).
2.  **Restore Database:** Restore the latest database backup (from S3 or cross-region RDS snapshot replication) to the newly provisioned RDS instance.
3.  **Deploy Application:** Trigger the CI/CD pipeline to deploy the latest application image to the new EC2 instance.
4.  **DNS Failover:** Update DNS records to point to the new region's load balancer/EC2 instance.

## 2. Troubleshooting Guide

### General Troubleshooting Steps

1.  **Check Logs First:** Always start by checking application logs (`docker logs <container_name>`), Nginx logs, and system logs (`journalctl -u docker`).
2.  **Verify Service Status:**
    *   `docker ps`: Check if containers are running.
    *   `docker-compose ps`: Check service status if using Docker Compose.
    *   `sudo systemctl status docker`: Check Docker daemon status.
3.  **Check Resource Usage:**
    *   `docker stats`: For container-level CPU/memory.
    *   `htop` or `top`: For host-level CPU/memory.
    *   `df -h`: Check disk space.
4.  **Network Connectivity:**
    *   `ping <ip_address>`: Check basic network reachability.
    *   `curl http://localhost:8000/health`: Check application health from within the container or host.
    *   `telnet <host> <port>`: Check if a port is open and listening.
5.  **Configuration Review:** Double-check `.env` files, Nginx configs, and Docker Compose files for typos or incorrect values.

### Common Issues and Solutions

#### Application Not Responding (5xx Errors)

*   **Symptoms:** HTTP 500, 502, 503, 504 errors, application not accessible.
*   **Possible Causes:**
    *   Application crashed or not running.
    *   Nginx (or load balancer) cannot reach the backend.
    *   Backend is overloaded.
*   **Troubleshooting:**
    1.  **Check `backend` container status:** `docker-compose ps backend` or `docker ps`. Is it `Up`? Is it restarting?
    2.  **Check `backend` logs:** `docker-compose logs backend` or `docker logs <backend_container_id>`. Look for Python tracebacks, startup errors, or "address already in use" errors.
    3.  **Check Nginx logs:** If using Nginx, check `docker-compose logs nginx` or `docker logs <nginx_container_id>`. Look for `upstream timed out` or `connection refused` errors.
    4.  **Verify backend health endpoint:** From inside the Nginx container or host, `curl http://backend:8000/health`.
    5.  **Check resource usage:** See if CPU/memory is maxed out.

#### Database Connection Issues

*   **Symptoms:** Application errors related to database connectivity, `psycopg2.OperationalError`, `connection refused`.
*   **Possible Causes:**
    *   Database container not running.
    *   Incorrect database credentials (`DB_USER`, `DB_PASSWORD`, `DB_NAME`).
    *   Incorrect database host (`DB_HOST`) or port (`DB_PORT`).
    *   Firewall/Security Group blocking database port.
*   **Troubleshooting:**
    1.  **Check `db` container status:** `docker-compose ps db`.
    2.  **Check `db` logs:** `docker-compose logs db`. Look for startup errors or authentication failures.
    3.  **Verify database health:** `docker exec <db_container_id> pg_isready -U $POSTGRES_USER -d $POSTGRES_DB`.
    4.  **Test connectivity from backend container:**
        ```bash
        docker exec -it <backend_container_id> bash
        # Inside backend container:
        psql -h db -U $POSTGRES_USER -d $POSTGRES_DB
        # Enter password when prompted. If it connects, the issue is likely app-side.
        ```
    5.  **Review `.env.prod`:** Ensure `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` are correct.
    6.  **Check Security Groups/Firewall:** Ensure the application server's security group allows outbound connections to the database port (5432) and the database's security group allows inbound connections from the application server.

#### High CPU/Memory Usage

*   **Symptoms:** Slow responses, application crashes, `docker stats` showing high resource consumption.
*   **Possible Causes:**
    *   Memory leaks in application code.
    *   Inefficient database queries.
    *   Spike in traffic.
    *   Infinite loops or resource-intensive background tasks.
*   **Troubleshooting:**
    1.  **Monitor with Grafana:** Check CPU, memory, and network graphs for the application and database.
    2.  **Check `docker stats`:** Identify which container is consuming resources.
    3.  **Review application logs:** Look for repeated errors, warnings, or long-running operations.
    4.  **Profile application:** Use Python profiling tools (e.g., `cProfile`, `py-spy`) in a development environment to identify bottlenecks.
    5.  **Optimize database queries:** Use `EXPLAIN ANALYZE` in PostgreSQL to optimize slow queries.
    6.  **Scale resources:** If due to traffic, consider scaling up the instance type or scaling out (adding more instances).

#### Slow API Responses

*   **Symptoms:** API calls take a long time to return, high latency reported by monitoring.
*   **Possible Causes:**
    *   Database bottlenecks.
    *   External API dependencies are slow.
    *   Inefficient application logic.
    *   Network latency.
*   **Troubleshooting:**
    1.  **Check monitoring dashboards:** Identify which service (backend, DB, Nginx) has high latency.
    2.  **Trace requests:** Implement distributed tracing (e.g., OpenTelemetry) to pinpoint where time is spent in a request.
    3.  **Review database performance:** Check DB query logs, slow query logs, and resource usage.
    4.  **Check external service health:** Verify the status of any third-party APIs the application depends on.
    5.  **Run performance tests:** Use Locust to simulate load and identify specific slow endpoints.

#### Deployment Failures

*   **Symptoms:** CI/CD pipeline fails, new version not deployed.
*   **Possible Causes:**
    *   Code errors (tests failing, linting issues).
    *   Docker build errors (missing dependencies, incorrect paths).
    *   Container registry authentication issues.
    *   Terraform errors (syntax, AWS permissions, resource conflicts).
    *   Deployment script errors (SSH issues, incorrect commands).
*   **Troubleshooting:**
    1.  **Review CI/CD pipeline logs:** GitHub Actions logs provide detailed output for each step. Identify the failing step.
    2.  **Reproduce locally:** If a Docker build fails, try building it locally (`docker build -f backend/Dockerfile .`).
    3.  **Check permissions:** Ensure GitHub Actions has correct permissions for Docker registry push and AWS access.
    4.  **Terraform state:** If Terraform fails, check `terraform plan` output and ensure your state file is not corrupted.

#### Monitoring Data Missing

*   **Symptoms:** Grafana dashboards show "No Data", Prometheus targets are down.
*   **Possible Causes:**
    *   Prometheus not running.
    *   Incorrect `prometheus.yml` configuration (wrong targets, ports).
    *   Firewall/Security Group blocking Prometheus from scraping targets.
    *   Application not exposing metrics correctly.
    *   Grafana not connected to Prometheus.
*   **Troubleshooting:**
    1.  **Check Prometheus container status:** `docker-compose ps prometheus`.
    2.  **Check Prometheus UI:** Go to `http://localhost:9090/targets` (or your Prometheus URL). Are your targets (backend, node_exporter, etc.) `UP`? If not, check the error message.
    3.  **Check Prometheus logs:** `docker-compose logs prometheus`.
    4.  **Verify Grafana datasource:** In Grafana UI, go to Configuration -> Data sources -> Prometheus. Test the connection.
    5.  **Check application metrics endpoint:** `curl http://backend:8000/metrics` (if applicable).

## 3. Runbook

This section outlines standard operating procedures for common tasks.

### Deployment Rollback

In case of a critical issue after a new deployment:

1.  **Identify the last known good image tag:** Check the CI/CD history or your container registry for the previous successful deployment's image tag (e.g., `ghcr.io/your-org/your-repo:previous_sha`).
2.  **Rollback Infrastructure (if applicable):**
    *   If infrastructure changes were part of the problematic deployment, revert the Terraform code to the previous commit and run `terraform apply`. This is complex and should be avoided if possible by separating infra and app deployments.
3.  **Rollback Application:**
    *   **Docker Compose/EC2:** SSH into the EC2 instance.
        ```bash
        # Stop current container
        sudo docker stop fastapi-monolith-app || true
        sudo docker rm fastapi-monolith-app || true
        # Pull and run the previous stable image
        sudo docker pull ghcr.io/your-org/your-repo:previous_sha
        sudo docker run -d --name fastapi-monolith-app -p 80:8000 \
          -e DB_USER='...' -e DB_PASSWORD='...' -e DB_HOST='...' -e DB_NAME='...' \
          ghcr.io/your-org/your-repo:previous_sha
        ```
    *   **CI/CD:** Trigger a manual deployment from the CI/CD pipeline, explicitly specifying the `previous_sha` as the image tag.
4.  **Monitor:** Closely monitor logs and metrics after rollback to confirm stability.
5.  **Post-Mortem:** Analyze the root cause of the issue and implement preventative measures.

### Restarting Services

*   **Single Service (e.g., backend):**
    ```bash
    docker-compose restart backend
    ```
*   **All Services:**
    ```bash
    docker-compose restart
    ```
*   **Force Recreate (if issues persist):**
    ```bash
    docker-compose up -d --force-recreate backend
    ```

### Scaling Up/Down

*   **Vertical Scaling (Increase resources):**
    1.  **EC2:** Change `instance_type` in `terraform/main.tf` and run `terraform apply`. This will replace the instance.
    2.  **Docker Compose:** Adjust resource limits in `docker-compose.prod.yml` (e.g., `cpus`, `memory`).
*   **Horizontal Scaling (Add more instances):**
    *   For EC2, this typically involves setting up an Auto Scaling Group and a Load Balancer. This setup is beyond the scope of the current `terraform/main.tf` but is the next step for production scaling.
    *   For Docker Compose, you can scale services: `docker-compose up -d --scale backend=3`. (Requires a load balancer like Nginx to distribute traffic).

### Incident Response Checklist

When an incident occurs:

1.  **Assess Impact:**
    *   How many users/services are affected?
    *   What is the severity (critical, major, minor)?
    *   Is data integrity at risk?
2.  **Gather Information:**
    *   Check monitoring dashboards (Grafana, Prometheus).
    *   Review application, Nginx, and database logs.
    *   Check recent deployments/changes.
3.  **Identify Root Cause (Hypothesize):**
    *   Is it a recent code change?
    *   Infrastructure issue?
    *   External dependency?
    *   Resource exhaustion?
4.  **Mitigate (Restore Service):**
    *   Rollback to previous stable version.
    *   Restart affected services.
    *   Scale up resources.
    *   Temporarily disable problematic features.
5.  **Communicate:**
    *   Notify stakeholders (internal teams, affected users).
    *   Provide regular updates.
6.  **Resolve:**
    *   Implement a permanent fix.
    *   Verify resolution.
7.  **Post-Mortem:**
    *   Document the incident, timeline, impact, root cause, and resolution.
    *   Identify lessons learned and action items to prevent recurrence.
    *   Update runbooks and documentation.
# FastAPI Monitoring Service - Operational Infrastructure

This repository provides a complete, production-ready operational infrastructure for a FastAPI application, with a strong focus on monitoring, alerting, and automated deployment.

## Table of Contents

1.  [Project Overview](#project-overview)
2.  [Features](#features)
3.  [Getting Started](#getting-started)
    *   [Prerequisites](#prerequisites)
    *   [Development Setup](#development-setup)
    *   [Production Deployment](#production-deployment)
4.  [CI/CD Pipeline](#ci-cd-pipeline)
5.  [Monitoring and Alerting](#monitoring-and-alerting)
    *   [Prometheus](#prometheus)
    *   [Grafana](#grafana)
    *   [Alertmanager](#alertmanager)
6.  [Security](#security)
7.  [API Documentation](#api-documentation)
8.  [Backup and Recovery](#backup-and-recovery)
9.  [Troubleshooting and Runbook](#troubleshooting-and-runbook)
10. [Code Quality](#code-quality)
11. [Contributing](#contributing)
12. [License](#license)

## 1. Project Overview

This project demonstrates an enterprise-grade operational setup for a Python FastAPI application. It includes:
*   Containerization with Docker (multi-stage builds).
*   Automated CI/CD using GitHub Actions.
*   Comprehensive testing (unit, integration, performance).
*   Robust monitoring and alerting with Prometheus, Grafana, and Alertmanager.
*   Security best practices and automated scanning.
*   Infrastructure as Code (via `docker-compose` for the stack).
*   Detailed documentation for setup, usage, and troubleshooting.

## 2. Features

*   **FastAPI Application**: A simple FastAPI service exposing health and Prometheus metrics endpoints.
*   **Dockerization**: Optimized multi-stage `Dockerfile` for small, secure images.
*   **Docker Compose**: `docker-compose.yml` for local development and `docker-compose.prod.yml` for production deployment.
*   **CI/CD**: GitHub Actions workflow for automated linting, security scanning, testing, image building, and deployment.
*   **Testing**: Pytest for unit and integration tests, simple Python script for performance testing.
*   **Monitoring**: Prometheus for metrics collection, Grafana for visualization, and Alertmanager for alerting.
*   **Security**: Automated vulnerability scanning (Trivy) and static analysis (Bandit). HTTPS (assumed to be handled by a reverse proxy in front of the stack).
*   **API Documentation**: OpenAPI/Swagger UI integrated with FastAPI.
*   **Environment Management**: `.env.template` for clear environment variable configuration.
*   **Deployment Automation**: Scripted deployment via SSH in CI/CD, with basic rollback considerations.
*   **Backup & Recovery**: Procedures outlined for data persistence.
*   **Code Quality**: Automated linting (Flake8) and formatting (Black).

## 3. Getting Started

### Prerequisites

*   Docker and Docker Compose (v2.x recommended)
*   Python 3.10+
*   `pip`
*   `git`
*   `curl` (for health checks)

### Development Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/fastapi-monitoring-app.git
    cd fastapi-monitoring-app
    ```

2.  **Create `.env` file:**
    Copy the template and fill in desired values.
    ```bash
    cp .env.template .env
    # Open .env and adjust ports if necessary
    ```

3.  **Build and run services with Docker Compose:**
    ```bash
    docker-compose up --build -d
    ```
    This will start:
    *   `app`: FastAPI application (http://localhost:8000)
    *   `prometheus`: Prometheus server (http://localhost:9090)
    *   `grafana`: Grafana dashboard (http://localhost:3000, default login: `admin`/`password`)

4.  **Verify services:**
    *   FastAPI Health: `curl http://localhost:8000/health`
    *   FastAPI Metrics: `curl http://localhost:8000/metrics`
    *   Prometheus UI: Open your browser to `http://localhost:9090`
    *   Grafana UI: Open your browser to `http://localhost:3000` (login with `admin`/`password`)

### Production Deployment

Production deployment is automated via the CI/CD pipeline. However, for manual deployment or understanding the process:

1.  **Prepare your production server:**
    *   Install Docker and Docker Compose.
    *   Ensure necessary ports (8000, 9090, 3000, 9093) are open in your firewall.
    *   Create a deployment directory, e.g., `/opt/fastapi-app/`.

2.  **Set up environment variables:**
    Create a `.env.prod` file on your server (or use environment variables directly) with production-specific values, especially for Grafana admin credentials.
    ```bash
    # .env.prod example
    APP_PORT=8000
    PROMETHEUS_PORT=9090
    GRAFANA_PORT=3000
    ALERTMANAGER_PORT=9093
    GRAFANA_ADMIN_USER=your_secure_admin_user
    GRAFANA_ADMIN_PASSWORD=your_strong_secure_password
    ```

3.  **Copy files to server:**
    Copy `docker-compose.prod.yml`, `.env.prod`, `prometheus/`, `grafana/`, `alertmanager/` to your server's deployment directory.

4.  **Pull Docker image:**
    Ensure your application's Docker image is available on the server. The CI/CD pipeline pushes to a registry (e.g., GitHub Container Registry or Docker Hub).
    ```bash
    docker pull your-dockerhub-username/fastapi-monitoring-app:latest
    ```

5.  **Deploy with Docker Compose:**
    ```bash
    cd /opt/fastapi-app/
    docker-compose -f docker-compose.prod.yml up --build -d
    ```

6.  **Configure Reverse Proxy (Recommended for Production):**
    For HTTPS and proper domain routing, it's highly recommended to place a reverse proxy (e.g., Nginx, Caddy, Traefik) in front of your Docker services. This setup assumes the reverse proxy handles SSL termination and routes traffic to the correct internal Docker ports.

## 4. CI/CD Pipeline

The `.github/workflows/ci-cd.yml` defines the automated CI/CD pipeline using GitHub Actions:

*   **`lint_and_format`**: Runs `black --check` and `flake8` for code style and quality.
*   **`security_scan`**:
    *   Runs `bandit` for Python static security analysis.
    *   Builds the Docker image and scans it for vulnerabilities using `Trivy`.
*   **`test`**: Executes unit, integration, and performance tests using `pytest` and a custom script.
*   **`build_and_push_image`**: Builds the production-ready Docker image and pushes it to a container registry (e.g., GitHub Container Registry) on `main` branch pushes.
*   **`deploy`**: Deploys the application to a production server via SSH on `main` branch pushes. It pulls the latest image, stops old containers, starts new ones, and performs a health check. Includes a basic rollback mechanism.

**Secrets Required for CI/CD (GitHub Actions -> Settings -> Secrets -> Actions):**
*   `SSH_PRIVATE_KEY`: SSH private key for connecting to your production server.
*   `PROD_SERVER_USER`: SSH username for your production server.
*   `PROD_SERVER_HOST`: IP address or hostname of your production server.
*   `GRAFANA_ADMIN_USER`: Admin username for Grafana in production.
*   `GRAFANA_ADMIN_PASSWORD`: Admin password for Grafana in production.
*   `DOCKER_HUB_USERNAME` (if using Docker Hub): Your Docker Hub username.
*   `DOCKER_HUB_TOKEN` (if using Docker Hub): Your Docker Hub access token.

## 5. Monitoring and Alerting

The stack includes Prometheus for metrics collection, Grafana for visualization, and Alertmanager for alerting.

### Prometheus

*   **Configuration**: `prometheus/prometheus.yml` defines scrape targets (FastAPI app, Prometheus itself, Grafana, Alertmanager).
*   **Alerting Rules**: `prometheus/rules.yml` contains example alerting rules (e.g., high latency, app down). These rules are evaluated by Prometheus and sent to Alertmanager if triggered.
*   **Access**: `http://localhost:9090` (dev) or `http://your-server-ip:9090` (prod).

### Grafana

*   **Configuration**: `grafana/provisioning/` contains files to automatically provision Prometheus as a data source and import the `fastapi_dashboard.json`.
*   **Dashboards**: `grafana/dashboards/fastapi_dashboard.json` provides a pre-configured dashboard for the FastAPI application, showing request rates, latency, error rates, etc.
*   **Access**: `http://localhost:3000` (dev) or `http://your-server-ip:3000` (prod).
    *   Default Dev Login: `admin`/`password`
    *   Production Login: Configured via `GRAFANA_ADMIN_USER` and `GRAFANA_ADMIN_PASSWORD` environment variables.

### Alertmanager

*   **Configuration**: `alertmanager/alertmanager.yml` defines how alerts are routed and sent (e.g., to email, Slack, PagerDuty).
*   **Access**: `http://localhost:9093` (dev) or `http://your-server-ip:9093` (prod).
*   **Example Configuration**: The provided `alertmanager.yml` includes a basic webhook receiver. You should configure this to send alerts to your preferred notification channels.

## 6. Security

*   **Vulnerability Scanning**: `Trivy` is integrated into the CI/CD pipeline to scan Docker images for known vulnerabilities.
*   **Static Analysis**: `Bandit` is used for static security analysis of Python code.
*   **Secrets Management**: Environment variables are used for sensitive data. In production, consider using a dedicated secrets management solution (e.g., HashiCorp Vault, AWS Secrets Manager, Kubernetes Secrets with external providers) for more robust secret handling.
*   **HTTPS**: It is critical to enable HTTPS for all public-facing services. This setup assumes a reverse proxy handles SSL termination.
*   **Least Privilege**: Docker images are built with minimal necessary components.
*   **Network Segmentation**: In a real production environment, ensure proper network segmentation and firewall rules to restrict access to services.

## 7. API Documentation

The FastAPI application automatically generates OpenAPI (Swagger) documentation.
*   **Swagger UI**: Access at `http://localhost:8000/docs`
*   **ReDoc**: Access at `http://localhost:8000/redoc`
*   **OpenAPI JSON**: Access at `http://localhost:8000/openapi.json` (also provided as `docs/openapi.yaml` for static reference).

## 8. Backup and Recovery

*   **Data Persistence**: Prometheus and Grafana data are persisted using Docker volumes (`prometheus_data`, `grafana_data`, `alertmanager_data`).
*   **Backup Procedure**:
    1.  Stop the respective service: `docker-compose stop prometheus grafana alertmanager`
    2.  Backup the Docker volumes. The exact method depends on your Docker volume setup (e.g., `docker cp` for named volumes, or backing up the host directory if using bind mounts).
        *   For named volumes, you can use a temporary container:
            ```bash
            docker run --rm --volumes-from prometheus_prod -v $(pwd)/backups:/backup ubuntu tar cvf /backup/prometheus_backup_$(date +%F).tar /prometheus
            ```
    3.  Store backups securely off-site.
*   **Recovery Procedure**:
    1.  Restore the backup data to the respective Docker volume path.
    2.  Start the services: `docker-compose up -d prometheus grafana alertmanager`
*   **Application Code**: The application code is version-controlled in Git, serving as its own backup. Docker images are stored in a registry.

## 9. Troubleshooting and Runbook

This section provides common troubleshooting steps and a runbook for operational issues.

**Common Issues & Solutions:**

*   **Application Not Starting (Docker Compose `app` service)**
    *   **Symptom**: `docker-compose ps` shows `app` as `unhealthy` or `Exited`.
    *   **Troubleshoot**:
        *   Check logs: `docker-compose logs app`
        *   Verify port conflicts: Ensure `APP_PORT` is not in use.
        *   Check `Dockerfile` and `requirements.txt` for build errors.
        *   Ensure `.env` variables are correctly set.
*   **Prometheus Not Scraping Metrics**
    *   **Symptom**: No data in Prometheus UI for `app` target, or target shows `DOWN`.
    *   **Troubleshoot**:
        *   Check Prometheus targets status: `http://localhost:9090/targets`
        *   Verify `app` container is running and its `/metrics` endpoint is accessible from Prometheus container.
        *   Check `prometheus/prometheus.yml` for correct `job_name` and `targets`.
        *   Check `app` logs for errors related to `/metrics` endpoint.
*   **Grafana Dashboards Not Showing Data**
    *   **Symptom**: Dashboard panels show "No Data" or errors.
    *   **Troubleshoot**:
        *   Verify Prometheus data source in Grafana: `Configuration -> Data sources`. Test connection.
        *   Check Grafana logs: `docker-compose logs grafana`.
        *   Ensure Prometheus is collecting data for the relevant metrics.
        *   Verify dashboard queries match Prometheus metric names.
*   **Alerts Not Firing/Sending**
    *   **Symptom**: Alerts are triggered in Prometheus but not received via configured channels.
    *   **Troubleshoot**:
        *   Check Alertmanager UI: `http://localhost:9093/#/alerts` to see active alerts.
        *   Check Alertmanager configuration: `alertmanager/alertmanager.yml` for correct receivers and routes.
        *   Check Alertmanager logs: `docker-compose logs alertmanager`.
        *   Verify connectivity to notification endpoints (e.g., email server, Slack webhook).
*   **CI/CD Pipeline Failures**
    *   **Symptom**: GitHub Actions workflow fails at a specific step.
    *   **Troubleshoot**:
        *   Review the logs for the failed step in the GitHub Actions UI.
        *   **Lint/Format**: Check code for style violations.
        *   **Security Scan**: Review Bandit/Trivy reports for critical findings.
        *   **Test**: Run tests locally to reproduce failures.
        *   **Build/Push**: Check Dockerfile syntax, Docker Hub/GHCR credentials.
        *   **Deploy**: Verify SSH connectivity, server disk space, correct environment variables on the server, and `docker-compose.prod.yml` syntax.

**Runbook - Deploying a New Version:**

1.  **Develop & Test Locally**: Ensure all new features/fixes work as expected in your local development environment.
2.  **Commit & Push to `develop`**: Push your changes to the `develop` branch.
    *   The CI/CD pipeline will run linting, security scans, and all tests.
    *   Address any failures immediately.
3.  **Create Pull Request (PR) to `main`**: Once `develop` is stable and all checks pass, create a PR to merge `develop` into `main`.
    *   Ensure all PR checks pass.
    *   Get code review from another team member.
4.  **Merge PR to `main`**: Merging to `main` triggers the production deployment.
    *   The CI/CD pipeline will:
        *   Re-run all checks.
        *   Build the production Docker image.
        *   Push the image to the container registry.
        *   Initiate deployment to the production server.
5.  **Monitor Deployment**:
    *   Watch the `deploy` job in GitHub Actions for success/failure.
    *   Check application health endpoint (`/health`) after deployment.
    *   Monitor Prometheus and Grafana dashboards for application health and performance metrics.
    *   Check Alertmanager for any new alerts.
6.  **Rollback (if needed)**:
    *   If the new deployment causes critical issues (e.g., app crash, high error rates):
        *   The CI/CD `deploy` step has a basic rollback attempt.
        *   Manually SSH into the server.
        *   Identify the previous stable Docker image tag.
        *   Edit `docker-compose.prod.yml` to use the previous stable image tag, or revert the `docker-compose.prod.yml` to a previous Git commit.
        *   Run `docker-compose -f docker-compose.prod.yml up -d` to revert.
        *   Investigate the root cause of the failed deployment.

## 10. Code Quality

*   **Black**: Enforces consistent code formatting.
*   **Flake8**: Checks for PEP 8 compliance and common Python errors.
*   Integrated into the CI/CD pipeline to ensure all code adheres to defined standards.

## 11. Contributing

Contributions are welcome! Please follow these steps:
1.  Fork the repository.
2.  Create a new branch for your feature or bug fix.
3.  Make your changes and ensure tests pass.
4.  Run `black .` and `flake8 .` to ensure code quality.
5.  Commit your changes.
6.  Push your branch and create a Pull Request.

## 12. License

This project is licensed under the MIT License - see the LICENSE file for details. (Note: A `LICENSE` file is not generated, but should be added in a real project.)
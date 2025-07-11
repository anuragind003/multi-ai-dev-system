# FastAPI Operational Infrastructure Demo

This repository provides a complete, production-ready operational infrastructure for a FastAPI application, demonstrating best practices for containerization, CI/CD, monitoring, security, and documentation.

## Table of Contents

1.  [Project Overview](#project-overview)
2.  [Features](#features)
3.  [Local Development Setup](#local-development-setup)
4.  [Production Deployment](#production-deployment)
5.  [CI/CD Pipeline](#ci/cd-pipeline)
6.  [Monitoring & Observability](#monitoring--observability)
7.  [Security Considerations](#security-considerations)
8.  [API Documentation](#api-documentation)
9.  [Testing](#testing)
10. [Backup & Recovery](#backup--recovery)
11. [Troubleshooting](#troubleshooting)
12. [Future Enhancements](#future-enhancements)

## 1. Project Overview

This project sets up a basic FastAPI application with a PostgreSQL database, demonstrating a robust DevOps workflow. It's designed to be a template for enterprise-grade applications, focusing on automation, reliability, and maintainability.

## 2. Features

*   **Containerization:** Multi-stage Dockerfile for optimized image size and build times.
*   **Environment Management:** `.env` files for configuration, Docker secrets for production.
*   **Local Development:** `docker-compose.yml` for easy setup with hot-reloading, PostgreSQL, and PgAdmin.
*   **Production Deployment:** `docker-compose.prod.yml` with Nginx reverse proxy, Prometheus, and Grafana.
*   **CI/CD:** GitHub Actions workflow for linting, testing, building, scanning, and deploying.
*   **Testing:** Comprehensive unit, integration, and performance (Locust) tests.
*   **Monitoring:** Prometheus for metrics collection, Grafana for visualization.
*   **Security:** Nginx for HTTPS termination, security headers, non-root user in Docker, vulnerability scanning (Trivy).
*   **Code Quality:** Automated linting and formatting with Black, Flake8, and Isort.
*   **Documentation:** Professional README, auto-generated OpenAPI/Swagger UI, and troubleshooting guide.
*   **Backup & Recovery:** Procedures outlined for database backups.

## 3. Local Development Setup

To get the application running locally for development:

1.  **Prerequisites:**
    *   Docker Desktop (or Docker Engine & Docker Compose) installed.
    *   `git` installed.

2.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-org/fastapi-operational-infrastructure.git
    cd fastapi-operational-infrastructure
    ```

3.  **Create `.env` file:**
    Copy the example environment file:
    ```bash
    cp .env.example .env
    ```
    Edit `.env` and fill in your desired values (e.g., `POSTGRES_PASSWORD`, `PGADMIN_DEFAULT_PASSWORD`).

4.  **Start the services:**
    ```bash
    docker compose up --build -d
    ```
    This will:
    *   Build the `app` Docker image.
    *   Start the `db` (PostgreSQL) container.
    *   Start the `app` (FastAPI) container.
    *   Start `pgadmin` for database management.

5.  **Access the application:**
    *   FastAPI App: `http://localhost:8000`
    *   FastAPI Docs (Swagger UI): `http://localhost:8000/docs`
    *   FastAPI ReDoc: `http://localhost:8000/redoc`
    *   PgAdmin: `http://localhost:8080` (Use `PGADMIN_DEFAULT_EMAIL` and `PGADMIN_DEFAULT_PASSWORD` from your `.env` file to log in).

6.  **Stop the services:**
    ```bash
    docker compose down
    ```

## 4. Production Deployment

The production deployment uses `docker-compose.prod.yml` which includes Nginx, Prometheus, and Grafana, along with the FastAPI app and PostgreSQL.

1.  **Prerequisites:**
    *   A Linux server (e.g., EC2 instance, DigitalOcean Droplet) with Docker and Docker Compose installed.
    *   SSH access to the server.
    *   DNS configured for your domain (e.g., `api.yourdomain.com`).

2.  **Prepare Secrets:**
    Create a `secrets` directory and place your sensitive production secrets there. These files are referenced in `docker-compose.prod.yml` and mounted as Docker secrets.
    ```bash
    mkdir secrets
    echo "your_strong_db_password" > secrets/db_password.txt
    echo "your_app_secret_key_for_prod" > secrets/app_secret_key.txt
    ```
    **IMPORTANT:** These files should *not* be committed to Git. Ensure `secrets/` is in your `.gitignore`.

3.  **Configure `.env` for Production:**
    Create a `.env` file on your production server (or use environment variables directly) with production-specific values.
    ```bash
    # .env on production server
    POSTGRES_USER=produser
    POSTGRES_DB=prod_db
    # POSTGRES_PASSWORD is handled by secrets/db_password.txt
    DATABASE_URL=postgresql://produser:$(cat /path/to/your/app/secrets/db_password.txt)@db:5432/prod_db

    # Grafana admin credentials
    GRAFANA_ADMIN_USER=admin
    GRAFANA_ADMIN_PASSWORD=your_grafana_admin_password
    ```

4.  **Configure Nginx:**
    Review and adjust `nginx/nginx.conf` for your domain and SSL certificate paths. For production, you should use a tool like Certbot to obtain and manage Let's Encrypt SSL certificates.

5.  **Deploy (Manual or via CI/CD):**
    *   **Manual Deployment:**
        ```bash
        # On your local machine, copy files to server
        scp -r .env docker-compose.prod.yml nginx prometheus secrets app requirements.txt Dockerfile locustfile.py pyproject.toml your_user@your_prod_host:/path/to/your/app/directory/

        # SSH into your production server
        ssh your_user@your_prod_host
        cd /path/to/your/app/directory

        # Pull the latest image (from GitHub Container Registry if using CI/CD)
        docker compose -f docker-compose.prod.yml pull

        # Start services
        docker compose -f docker-compose.prod.yml up -d --remove-orphans

        # Clean up old images
        docker image prune -f
        ```
    *   **CI/CD Deployment:** The `.github/workflows/main.yml` pipeline includes a `deploy-prod` job that automates this process. It requires `SSH_PRIVATE_KEY`, `PROD_USER`, `PROD_HOST`, `DB_PASSWORD`, and `APP_SECRET_KEY` to be configured as GitHub Secrets.

## 5. CI/CD Pipeline

The CI/CD pipeline is defined in `.github/workflows/main.yml` and uses GitHub Actions.

**Workflow Stages:**

1.  **`lint-format`**:
    *   Runs `black`, `flake8`, and `isort` to ensure code quality and consistency. Fails if any issues are found.
2.  **`test`**:
    *   Sets up a temporary PostgreSQL container.
    *   Runs `pytest` for unit and integration tests.
3.  **`build-scan-push`**:
    *   Builds the Docker image using the multi-stage `Dockerfile`.
    *   Pushes the image to GitHub Container Registry (`ghcr.io`).
    *   Performs a vulnerability scan using Trivy. Fails on `CRITICAL` or `HIGH` severity vulnerabilities.
4.  **`deploy-prod`**:
    *   **Triggered:** On push to `main` branch.
    *   **Environment:** Uses GitHub Environments for protection rules (e.g., manual approval).
    *   Connects to the production server via SSH.
    *   Pulls the latest Docker image.
    *   Deploys the application using `docker-compose.prod.yml`.
    *   **Rollback:** In case of a failed deployment, you can manually revert to a previous image tag and restart the services on the server.
5.  **`performance-test`**:
    *   Runs Locust load tests against the deployed production application.
    *   Provides insights into API performance under load.

## 6. Monitoring & Observability

The production setup includes Prometheus for metrics collection and Grafana for visualization.

*   **Prometheus:**
    *   Configuration: `prometheus/prometheus.yml`
    *   Scrapes metrics from the FastAPI application (if you integrate a metrics library like `fastapi-prometheus` or `starlette-exporter`).
    *   Scrapes cAdvisor (for container metrics, if enabled in Docker Compose) and Node Exporter (for host metrics, if running on the host).
    *   Access: `http://your-prod-host:9090`
*   **Grafana:**
    *   Access: `http://your-prod-host:3000`
    *   Default credentials: `admin`/`your_grafana_admin_password` (from `.env`).
    *   You'll need to configure Prometheus as a data source in Grafana and import relevant dashboards (e.g., Node Exporter Full, cAdvisor, or custom dashboards for your FastAPI app).

**To add FastAPI application metrics:**
You would integrate a library like `fastapi-prometheus` or `starlette-exporter` into your `app/main.py`.
Example:
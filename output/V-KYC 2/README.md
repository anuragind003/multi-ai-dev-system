# FastAPI ELK Centralized Logging Infrastructure

This repository provides a complete, production-ready operational infrastructure for a FastAPI application integrated with the ELK Stack (Elasticsearch, Logstash, Kibana) for centralized logging. It emphasizes containerization, CI/CD, comprehensive testing, monitoring, security, and infrastructure as code.

## Table of Contents

1.  [Project Overview](#project-overview)
2.  [Features](#features)
3.  [Prerequisites](#prerequisites)
4.  [Local Development Setup](#local-development-setup)
    *   [Running the Application and ELK Stack](#running-the-application-and-elk-stack)
    *   [Accessing Services](#accessing-services)
    *   [Sending Logs](#sending-logs)
5.  [Project Structure](#project-structure)
6.  [CI/CD Pipeline](#ci/cd-pipeline)
7.  [Testing](#testing)
    *   [Unit and Integration Tests](#unit-and-integration-tests)
    *   [Performance Testing](#performance-testing)
8.  [Infrastructure as Code (IaC)](#infrastructure-as-code-iac)
9.  [Security](#security)
10. [Monitoring and Observability](#monitoring-and-observability)
11. [Deployment](#deployment)
12. [Backup and Recovery](#backup-and-recovery)
13. [Troubleshooting and Runbook](#troubleshooting-and-runbook)
14. [Contributing](#contributing)
15. [License](#license)

## 1. Project Overview

This project demonstrates how to set up a robust logging solution for a Python FastAPI application using the ELK stack. The FastAPI application is containerized, and its logs are structured (JSON) and sent to Logstash, which then forwards them to Elasticsearch for indexing. Kibana provides a powerful UI for searching, analyzing, and visualizing these logs.

## 2. Features

*   **FastAPI Application:** A simple Python FastAPI application.
*   **Multi-stage Dockerfile:** Optimized Docker image for the FastAPI application.
*   **ELK Stack:**
    *   **Elasticsearch:** Distributed search and analytics engine.
    *   **Logstash:** Data processing pipeline for ingesting and transforming logs.
    *   **Kibana:** Data visualization dashboard for Elasticsearch.
*   **Docker Compose:** Orchestration for local development and single-host deployments.
*   **CI/CD Pipeline (GitHub Actions):** Automated build, test, security scan, and deployment.
*   **Comprehensive Testing:** Unit, integration, and performance (Locust) tests.
*   **Infrastructure as Code (Terraform):** Example for provisioning a Docker host on AWS.
*   **Environment Management:** `.env.template` for configuration.
*   **Monitoring & Observability:** Health checks, structured logging, and Kibana dashboards.
*   **Security Best Practices:** Docker image scanning, secret management considerations.
*   **Deployment Automation:** `deploy.sh` script for simplified deployments.
*   **API Documentation:** OpenAPI/Swagger specification.
*   **Code Quality:** Linting, formatting, and type checking.
*   **Backup & Recovery:** Documented procedures for data persistence.
*   **Troubleshooting:** Common issues and solutions.

## 3. Prerequisites

Before you begin, ensure you have the following installed:

*   [Git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
*   [Docker Desktop](https://www.docker.com/products/docker-desktop) (includes Docker Engine and Docker Compose)
*   [Python 3.10+](https://www.python.org/downloads/)
*   [Poetry](https://python-poetry.org/docs/#installation) (Python dependency management)
*   [Terraform](https://www.terraform.io/downloads) (if deploying to AWS)
*   [curl](https://curl.se/download.html) (for health checks)

## 4. Local Development Setup

### Running the Application and ELK Stack

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/fastapi-elk-app.git
    cd fastapi-elk-app
    ```

2.  **Create `.env` file:**
    Copy the template and fill in any necessary values. For local development, the defaults in `.env.template` are usually sufficient.
    ```bash
    cp .env.template .env
    # You can edit .env if needed, e.g., to change LOGSTASH_HOST if not using default bridge network
    ```

3.  **Start the Docker Compose services:**
    This will build the FastAPI app image and start Elasticsearch, Logstash, Kibana, and the FastAPI app.
    ```bash
    docker compose up --build -d
    ```
    *   `--build`: Ensures the FastAPI image is rebuilt if changes occurred.
    *   `-d`: Runs the containers in detached mode.

4.  **Verify containers are running:**
    ```bash
    docker compose ps
    ```
    You should see `fastapi_app`, `elasticsearch`, `logstash`, and `kibana` in a healthy state. It might take a few minutes for Elasticsearch and Kibana to fully initialize and pass their health checks.

### Accessing Services

Once all services are up and healthy:

*   **FastAPI Application:** `http://localhost:8000`
    *   API Docs (Swagger UI): `http://localhost:8000/docs`
    *   Redoc: `http://localhost:8000/redoc`
    *   Health Check: `http://localhost:8000/health`
*   **Kibana:** `http://localhost:5601`
    *   Once Kibana loads, go to **Management -> Stack Management -> Index Patterns** and create an index pattern for `fastapi-logs-*`.
    *   Then, navigate to **Analytics -> Discover** to view your application logs.
*   **Elasticsearch:** `http://localhost:9200` (for direct API access, e.g., `http://localhost:9200/_cat/indices?v`)

### Sending Logs

The FastAPI application is configured to send structured JSON logs to Logstash via TCP on port `5000`.
Simply access the FastAPI endpoints, and logs will appear in Kibana:

*   `http://localhost:8000/`
*   `http://localhost:8000/items/123?q=test`
*   `http://localhost:8000/error` (to generate an error log)

## 5. Project Structure
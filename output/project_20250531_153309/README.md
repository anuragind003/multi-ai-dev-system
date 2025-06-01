# LTFS Offer CDP (Customer Data Platform)

## Table of Contents
- [1. Project Overview](#1-project-overview)
- [2. Functional Requirements](#2-functional-requirements)
- [3. Non-Functional Requirements](#3-non-functional-requirements)
- [4. Technology Stack](#4-technology-stack)
- [5. Architecture](#5-architecture)
- [6. Key Data Entities](#6-key-data-entities)
- [7. Setup and Local Development](#7-setup-and-local-development)
  - [7.1. Prerequisites](#71-prerequisites)
  - [7.2. Database Setup (PostgreSQL)](#72-database-setup-postgresql)
  - [7.3. Event Streaming Setup (Kafka)](#73-event-streaming-setup-kafka)
  - [7.4. Running Microservices](#74-running-microservices)
- [8. Build Commands](#8-build-commands)
- [9. Deployment Notes](#9-deployment-notes)
- [10. API Documentation](#10-api-documentation)
- [11. Contributing](#11-contributing)
- [12. License](#12-license)

## 1. Project Overview
The LTFS Offer Customer Data Platform (CDP) is a new strategic system designed to revolutionize the management of customer, campaign, and various offer data for Consumer Loan Products. Its primary goal is to eliminate manual processes, enable faster data processing, and significantly improve data quality and accessibility, providing a unified view of the customer.

## 2. Functional Requirements
The system is designed to fulfill the following core functionalities:
- **Unified Customer Profile:** Provide a single, consolidated profile view of the customer specifically for Consumer Loan Products through robust deduplication mechanisms.
- **Data Validation:** Perform basic column-level validation on all incoming data streams from the Offermart system to the CDP.
- **Comprehensive Deduplication:** Apply sophisticated deduplication logic across all Consumer Loan (CL) product categories, including Loyalty, Preapproved, and E-aggregator offers.
- **Live Book Deduplication:** Execute deduplication against the 'live book' (Customer 360 system) before offers are finalized and presented.
- **Top-up Offer Specific Deduplication:** Top-up loan offers must be deduped exclusively within other Top-up offers. Any matches found within this category should be removed to prevent redundancy.

## 3. Non-Functional Requirements
The system adheres to the following non-functional requirements to ensure robustness and reliability:
- **Performance:** Achieve significantly faster processing of customer, campaign, and offer data compared to existing manual processes.
- **Security:** Implement stringent security measures to ensure the confidentiality, integrity, and availability of all processed and stored customer and offer data. This includes data encryption at rest and in transit, access controls, and regular security audits.
- **Scalability:** The system must be highly scalable, capable of handling increasing volumes of customer, campaign, and offer data without degradation in performance. This is achieved through a microservices architecture and event-driven patterns.

## 4. Technology Stack
- **Backend:** Java 17+ with Spring Boot
- **Database:** PostgreSQL
- **Event Streaming:** Apache Kafka (for inter-service communication and data ingestion)
- **Build Tool:** Apache Maven
- **Containerization:** Docker

## 5. Architecture
The LTFS Offer CDP is built on a **Microservices Architecture** with **Event-Driven Components**.
- **Microservices:** The system is decomposed into independent, loosely coupled services, each responsible for a specific business capability (e.g., Customer Service, Offer Service, Campaign Service, Deduplication Service, Validation Service). This promotes modularity, independent deployment, and scalability.
- **Event-Driven:** Apache Kafka serves as the central nervous system for asynchronous communication between microservices. Data ingestion, deduplication triggers, offer finalization events, and status updates are propagated via Kafka topics, ensuring high throughput and resilience.

## 6. Key Data Entities
The core data entities managed and processed by the CDP system include:
- **Customer:** Comprehensive customer profiles, including deduplicated views.
- **Offer:** Details of various loan offers, including their status and associated campaigns.
- **Campaign:** Information about marketing campaigns linked to specific offers.

## 7. Setup and Local Development

### 7.1. Prerequisites
Ensure you have the following installed on your development machine:
- **Java Development Kit (JDK) 17 or higher:**
  ```bash
  java -version
  ```
- **Apache Maven 3.6 or higher:**
  ```bash
  mvn -version
  ```
- **Docker and Docker Compose:** For running local PostgreSQL and Kafka instances.
  ```bash
  docker -v
  docker compose -v
  ```
- **Git:** For cloning the repository.
  ```bash
  git -v
  ```

### 7.2. Database Setup (PostgreSQL)
The project uses PostgreSQL as its primary database. You can run a local instance using Docker Compose.

1.  **Navigate to the `docker` directory** (or wherever your `docker-compose.yml` for infrastructure is located, typically at the root or `infra` folder).
2.  **Start PostgreSQL:**
    ```bash
    docker compose up -d postgres
    ```
    This will start a PostgreSQL container. The database name, username, and password will be configured in the `docker-compose.yml` and should match the `application.yml` settings of your Spring Boot services.
    *   **Default Connection Details (check `docker-compose.yml` for exact values):**
        *   Host: `localhost` (or `postgres` if connecting from another Docker container)
        *   Port: `5432`
        *   Database Name: `cdp_db`
        *   Username: `cdp_user`
        *   Password: `cdp_password`
3.  **Database Migrations:** Each microservice is expected to manage its own schema using Flyway or Liquibase. Upon service startup, migrations will automatically apply.

### 7.3. Event Streaming Setup (Kafka)
Apache Kafka is used for inter-service communication.

1.  **Navigate to the `docker` directory** (or `infra` folder).
2.  **Start Kafka and Zookeeper:**
    ```bash
    docker compose up -d zookeeper kafka
    ```
    This will start Kafka and its dependency Zookeeper.
    *   **Kafka Broker Address:** `localhost:9092` (or `kafka:9092` if connecting from another Docker container)

### 7.4. Running Microservices
Each microservice is an independent Spring Boot application.

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd ltfs-offer-cdp
    ```
2.  **Build all microservices:**
    Navigate to the root of the project and build all modules.
    ```bash
    mvn clean install
    ```
    *Alternatively, navigate to each service directory (e.g., `cd services/customer-service`) and run `mvn clean install`.*
3.  **Configure Environment Variables:**
    Each service will require environment variables or `application.yml` configurations for database connections, Kafka broker addresses, and other service-specific settings. Ensure these are correctly set for your local environment.
    *   Example `application.yml` snippet (for `customer-service`):
        ```yaml
        spring:
          datasource:
            url: jdbc:postgresql://localhost:5432/cdp_db
            username: cdp_user
            password: cdp_password
          kafka:
            bootstrap-servers: localhost:9092
        ```
4.  **Run individual microservices:**
    Navigate to the directory of the specific microservice you want to run (e.g., `services/customer-service`).
    ```bash
    mvn spring-boot:run
    ```
    Repeat this step for all necessary microservices (e.g., `offer-service`, `campaign-service`, `deduplication-service`, `validation-service`).

## 8. Build Commands
- **Clean and Build All Modules:**
  ```bash
  mvn clean install
  ```
  This command compiles the code, runs tests, and packages the services into JAR files.
- **Build Docker Images (for each service):**
  Navigate to the root of a specific service (e.g., `services/customer-service`).
  ```bash
  mvn spring-boot:build-image
  ```
  This command leverages Spring Boot's integration with Cloud Native Buildpacks to create optimized Docker images.

## 9. Deployment Notes
The LTFS Offer CDP is designed for cloud-native deployments, leveraging containerization and orchestration.
- **Containerization:** All microservices are containerized using Docker, ensuring consistent environments from development to production.
- **Orchestration:** Deployment to production environments is typically managed via Kubernetes or similar container orchestration platforms, enabling automated scaling, healing, and rolling updates.
- **CI/CD Pipeline:** A robust CI/CD pipeline (e.g., Jenkins, GitLab CI, GitHub Actions) is used to automate the build, test, and deployment processes, ensuring rapid and reliable releases.
- **Configuration Management:** Externalized configuration (e.g., Spring Cloud Config, Kubernetes ConfigMaps/Secrets) is used to manage environment-specific settings for different deployment stages (dev, staging, prod).

## 10. API Documentation
Each microservice exposes its REST APIs, typically documented using OpenAPI (Swagger UI).
Once a service is running, you can usually access its Swagger UI at:
`http://localhost:<service_port>/swagger-ui.html`
(e.g., `http://localhost:8080/swagger-ui.html` for a service running on port 8080).

## 11. Contributing
Contributions are welcome! Please follow these steps:
1.  Fork the repository.
2.  Create a new branch (`git checkout -b feature/your-feature-name`).
3.  Make your changes.
4.  Commit your changes (`git commit -m 'Add new feature'`).
5.  Push to the branch (`git push origin feature/your-feature-name`).
6.  Open a Pull Request.

## 12. License
This project is licensed under the [MIT License](LICENSE).
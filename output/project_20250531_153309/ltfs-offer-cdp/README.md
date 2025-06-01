# LTFS Offer CDP (Customer Data Platform)

## Table of Contents
1.  [Introduction](#introduction)
2.  [Purpose](#purpose)
3.  [Key Features](#key-features)
4.  [Non-Functional Requirements](#non-functional-requirements)
5.  [Technology Stack](#technology-stack)
6.  [Architecture Overview](#architecture-overview)
7.  [Key Data Entities](#key-data-entities)
8.  [Getting Started](#getting-started)
    *   [Prerequisites](#prerequisites)
    *   [Cloning the Repository](#cloning-the-repository)
    *   [Database Setup](#database-setup)
    *   [Building the Services](#building-the-services)
    *   [Running the Services](#running-the-services)
9.  [API Documentation](#api-documentation)
10. [Contributing](#contributing)
11. [License](#license)

---

## 1. Introduction
The LTFS Offer Customer Data Platform (CDP) is a new, robust system designed to centralize and manage customer, campaign, and offer data for Consumer Loan Products. This platform aims to modernize and streamline the offer management lifecycle by eliminating manual processes, enabling faster data processing, and improving overall data quality and consistency.

## 2. Purpose
The primary purpose of the LTFS Offer CDP is to:
*   **Eliminate Manual Processes:** Automate the ingestion, validation, deduplication, and management of customer and offer data.
*   **Enable Faster Processing:** Significantly reduce the time taken to process customer and campaign data, leading to quicker offer finalization.
*   **Improve Data Management:** Provide a single, unified, and accurate view of the customer, ensuring data integrity and consistency across various Consumer Loan products.

## 3. Key Features
The system provides the following core functionalities:
*   **Unified Customer Profile:** Creates a single, deduplicated profile view of the customer for all Consumer Loan Products.
*   **Data Validation:** Performs basic column-level validation on data ingested from the Offermart system into the CDP.
*   **Comprehensive Deduplication:**
    *   Applies sophisticated deduplication logic across all Consumer Loan (CL) products, including Loyalty, Preapproved, and E-aggregator offers.
    *   Performs deduplication against the 'live book' (Customer 360) to ensure offers are not extended to existing customers who are ineligible or already have similar products.
    *   **Top-up Loan Specific Deduplication:** Top-up loan offers are deduped exclusively within other Top-up offers. Any matches found are removed to prevent duplicate or conflicting top-up offers.
*   **Offer Management:** Facilitates the efficient management and finalization of various loan offers.

## 4. Non-Functional Requirements
*   **Performance:** Designed for high throughput and low latency to achieve faster processing of customer, campaign, and offer data.
*   **Security:** Implements robust security measures to ensure the confidentiality, integrity, and availability of all sensitive customer and offer data processed and stored within the system.
*   **Scalability:** Built on a microservices architecture to handle increasing volumes of customer data, campaigns, and offers without degradation in performance. The system can be horizontally scaled to meet future demands.

## 5. Technology Stack
*   **Backend:** Java 17+ with Spring Boot 3+
*   **Database:** PostgreSQL
*   **Architecture:** Microservices Architecture with Event-Driven Components
*   **Build Tool:** Maven
*   **Containerization:** Docker, Docker Compose

## 6. Architecture Overview
The LTFS Offer CDP is built as a collection of independently deployable microservices. Each service is responsible for a specific business capability (e.g., Customer Service, Offer Service, Campaign Service, Deduplication Service, Validation Service). Communication between services is primarily asynchronous, leveraging event-driven patterns (e.g., Kafka or RabbitMQ, if implemented) to ensure loose coupling and resilience. Synchronous communication is used where immediate responses are required.

## 7. Key Data Entities
The core data entities managed by the system include:
*   **Customer:** Represents the individual customer, including their unique identifiers, contact information, and loan product history.
*   **Offer:** Details of a specific loan offer, including product type, terms, eligibility criteria, and status.
*   **Campaign:** Information about marketing campaigns, linking offers to specific customer segments and promotional activities.

## 8. Getting Started

### Prerequisites
Before you begin, ensure you have the following installed:
*   Java Development Kit (JDK) 17 or higher
*   Apache Maven 3.6.0 or higher
*   Docker Desktop (includes Docker Engine and Docker Compose)
*   A PostgreSQL client (optional, for direct database access)

### Cloning the Repository
```bash
git clone https://github.com/LTFS/ltfs-offer-cdp.git
cd ltfs-offer-cdp
```

### Database Setup
The project uses PostgreSQL. For local development, you can spin up a PostgreSQL instance using Docker Compose.
Navigate to the `docker` directory (or the root if `docker-compose.yml` is at the root) and run:
```bash
docker-compose up -d postgres
```
This will start a PostgreSQL container. Database connection details for each microservice will be configured in their respective `application.yml` or `application.properties` files. Ensure the database name, username, and password match the `docker-compose.yml` configuration.

### Building the Services
Each microservice within the `ltfs-offer-cdp` project is an independent Spring Boot application.
To build all services, navigate to the root directory of the cloned repository and run:
```bash
mvn clean install
```
This command will compile all modules, run tests, and package them into JAR files.

### Running the Services
After building, you can run each service individually.
Navigate into the directory of a specific service (e.g., `customer-service`, `offer-service`, `dedupe-service`) and run its JAR file:
```bash
cd customer-service
java -jar target/customer-service-0.0.1-SNAPSHOT.jar
```
Repeat this for all necessary services. For a full local environment, you might need to run several services concurrently. Consider using an IDE's multi-run configuration or a script for convenience.

## 9. API Documentation
Each microservice exposes its API documentation via Swagger/OpenAPI. Once a service is running, you can typically access its documentation at:
`http://localhost:<service-port>/swagger-ui.html` or `http://localhost:<service-port>/v3/api-docs`
Refer to the `application.yml` of each service for its specific port.

## 10. Contributing
We welcome contributions! Please refer to our `CONTRIBUTING.md` (if available) for guidelines on how to contribute to this project.

## 11. License
This project is licensed under the MIT License - see the `LICENSE` file for details.
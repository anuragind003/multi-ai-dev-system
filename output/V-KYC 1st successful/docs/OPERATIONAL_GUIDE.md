# Operational Guide: S3 Temporary File Storage API

This document provides essential information for operating, troubleshooting, and maintaining the S3 Temporary File Storage API.

## Table of Contents
1.  [Application Overview](#1-application-overview)
2.  [Deployment & Rollback](#2-deployment--rollback)
3.  [Monitoring & Alerting](#3-monitoring--alerting)
4.  [Logging](#4-logging)
5.  [Troubleshooting Guide](#5-troubleshooting-guide)
    *   [Common Issues](#common-issues)
    *   [Debugging Steps](#debugging-steps)
6.  [Backup and Recovery Procedures](#6-backup-and-recovery-procedures)
    *   [S3 Data Backup](#s3-data-backup)
    *   [Application Configuration Backup](#application-configuration-backup)
    *   [Recovery Steps](#recovery-steps)
7.  [Maintenance & Scaling](#7-maintenance--scaling)
8.  [Security Best Practices](#8-security-best-practices)

---

## 1. Application Overview

The S3 Temporary File Storage API is a FastAPI application designed to facilitate the temporary storage and retrieval of files on AWS S3. It's containerized using Docker and deployed on AWS infrastructure managed by Terraform.

*   **Language/Framework:** Python, FastAPI
*   **Containerization:** Docker
*   **Cloud Provider:** AWS
*   **Storage:** AWS S3
*   **IaC:** Terraform
*   **CI/CD:** GitHub Actions
*   **Monitoring:** Prometheus (metrics), CloudWatch (logs)

## 2. Deployment & Rollback

### Deployment Process
The deployment process is automated via the GitHub Actions CI/CD pipeline (`.github/workflows/ci-cd.yml`).
1.  A push to the `main` branch triggers the `deploy` job.
2.  The pipeline builds the Docker image and pushes it to AWS ECR.
3.  Terraform is executed to provision/update AWS resources (S3 bucket, IAM roles/policies, and potentially ECS/EKS services if configured).

### Rollback Procedures
*   **Application Rollback (Docker Image):**
    *   If a new deployment introduces issues, the fastest way to rollback is to deploy a previous, stable Docker image version.
    *   **ECS/EKS:** Update the ECS Task Definition or Kubernetes Deployment to reference a known good image tag from ECR. This can often be done via the AWS console, `aws cli`, `kubectl`, or by re-running the CI/CD pipeline with a specific older commit/tag.
    *   **Manual:** If running directly on EC2, pull the older image and restart the container.
*   **Infrastructure Rollback (Terraform):**
    *   Terraform maintains a state file. In case of infrastructure issues, you can revert to a previous state.
    *   **CAUTION:** Directly reverting Terraform state can be risky. Prefer to fix the issue in code and apply a new change. If a rollback is absolutely necessary, ensure you understand the implications.
    *   To revert to a previous state, checkout the Git commit corresponding to the desired state, then run `terraform plan` and `terraform apply`.
    *   For critical infrastructure, consider using Terraform Cloud or a remote backend with state locking for team collaboration and history.

## 3. Monitoring & Alerting

### Metrics
The application exposes Prometheus metrics at the `/metrics` endpoint.
Key metrics to monitor:
*   `s3_upload_requests_total`: Total number of file uploads (monitor for spikes or drops).
*   `s3_download_requests_total`: Total number of file downloads.
*   `s3_delete_requests_total`: Total number of file deletions.
*   `s3_upload_duration_seconds_bucket`: Latency of file uploads (monitor for increases).
*   `s3_download_duration_seconds_bucket`: Latency of file downloads.
*   `s3_file_size_bytes_bucket`: Distribution of file sizes.
*   `up{job="s3-temp-storage-app"}`: Basic service health (0 for down, 1 for up).

### Alerting
Configure Prometheus Alertmanager (or AWS CloudWatch Alarms) to send notifications for critical events:
*   **Application Down:** `up{job="s3-temp-storage-app"} == 0`
*   **High Error Rate:** `sum(rate(s3_upload_requests_total{status="error"}[5m])) > N` (adjust N based on acceptable error rate)
*   **High Latency:** `histogram_quantile(0.99, rate(s3_upload_duration_seconds_bucket[5m])) > X` (adjust X for acceptable 99th percentile latency)
*   **S3 Connectivity Issues:** Monitor application logs for S3 connection errors.

## 4. Logging

The application logs to `stdout`/`stderr`. In a production environment, ensure these logs are:
*   **Centralized:** Use a log aggregation service (e.g., AWS CloudWatch Logs, ELK stack, Splunk, Datadog).
*   **Structured:** Logs are generally unstructured text. Consider adding a structured logging library (e.g., `python-json-logger`) for easier parsing and analysis.
*   **Monitored:** Set up alarms on log patterns (e.g., "ERROR", "Failed to upload").

## 5. Troubleshooting Guide

### Common Issues

*   **Application Not Starting/Unhealthy:**
    *   **Symptom:** Health check fails, container crashes.
    *   **Possible Causes:** Incorrect environment variables (e.g., missing AWS credentials, wrong bucket name), network issues preventing S3 access, syntax errors in code.
    *   **Troubleshooting:**
        *   Check container logs (`docker logs <container_id>`, or CloudWatch logs in AWS).
        *   Verify `.env` file or environment variables passed to the container.
        *   Check network connectivity from the container to AWS S3 endpoints.
        *   Ensure IAM role/user has correct S3 permissions.
*   **File Upload/Download Failures:**
    *   **Symptom:** API returns 500 Internal Server Error or specific S3 errors.
    *   **Possible Causes:** Incorrect S3 bucket name, invalid AWS credentials, insufficient IAM permissions, S3 service outages, network issues.
    *   **Troubleshooting:**
        *   Check application logs for detailed error messages from `boto3`.
        *   Verify S3 bucket name and region.
        *   Confirm IAM policy attached to the application's execution role/user grants `s3:PutObject`, `s3:GetObject`, `s3:DeleteObject`, `s3:ListBucket`.
        *   Check AWS Service Health Dashboard for S3 outages in your region.
*   **Files Not Expiring:**
    *   **Symptom:** Files remain in S3 beyond their intended expiration.
    *   **Possible Causes:** S3 bucket lifecycle rule not configured correctly or not applied, incorrect `file_expiration_days` in Terraform.
    *   **Troubleshooting:**
        *   Verify the S3 bucket lifecycle rule in the AWS S3 console. Ensure it's enabled and the `Expiration` action is set correctly.
        *   Check Terraform state to confirm the `aws_s3_bucket_lifecycle_configuration` resource was applied successfully.
*   **Performance Degradation:**
    *   **Symptom:** High latency for upload/download, timeouts.
    *   **Possible Causes:** Insufficient application resources (CPU/memory), network bottlenecks, S3 throttling (unlikely for typical loads), database bottlenecks (if a database were added).
    *   **Troubleshooting:**
        *   Monitor Prometheus metrics (`s3_upload_duration_seconds`, `s3_download_duration_seconds`).
        *   Check container resource utilization (CPU, memory) in your orchestration platform.
        *   Scale up application instances if CPU/memory are consistently high.
        *   Review network configuration (e.g., VPC endpoints for S3).

### Debugging Steps

1.  **Check Logs:** Always start by reviewing application logs for error messages and stack traces.
2.  **Verify Environment:** Double-check all environment variables, especially AWS credentials and bucket names.
3.  **Test Connectivity:** From within the application container, try to ping S3 endpoints or use `aws cli` commands if available (for debugging purposes only, not in production images).
4.  **IAM Permissions:** Use AWS IAM Policy Simulator to verify that the IAM role/user has the necessary permissions for S3 actions.
5.  **Reproduce Locally:** Attempt to reproduce the issue in a local development environment using `docker-compose up`.
6.  **Check Dependencies:** Ensure all external services (AWS S3) are operational.

## 6. Backup and Recovery Procedures

The primary data storage is AWS S3, which offers high durability and built-in backup features.

### S3 Data Backup
*   **S3 Versioning:** Enabled on the `temp_storage_bucket` via Terraform. This automatically keeps multiple versions of an object, protecting against accidental deletions or overwrites.
    *   **Recovery:** To recover a previous version of a file, use the AWS S3 console or AWS CLI/SDK to list object versions and restore a specific one.
*   **S3 Cross-Region Replication (Optional):** For disaster recovery across AWS regions, consider configuring S3 Cross-Region Replication (CRR). This automatically replicates objects to a bucket in a different AWS region.
    *   **Configuration:** This would be an additional Terraform resource (`aws_s3_bucket_replication_configuration`).
*   **S3 Lifecycle Policies:** While used for deletion, they can also be configured to transition older versions to cheaper storage classes (e.g., S3 Glacier) for long-term archiving if needed.

### Application Configuration Backup
*   **Codebase:** The application code is version-controlled in Git (GitHub). This serves as the primary backup for the application logic.
*   **Terraform State:** The Terraform state file (`terraform.tfstate`) represents the current state of your infrastructure.
    *   **Best Practice:** Store the Terraform state in a remote backend (e.g., AWS S3 with DynamoDB locking) to prevent data loss and enable team collaboration. This project's CI/CD assumes a remote backend is configured or uses local state for simplicity.
*   **Environment Variables:** Critical environment variables are stored as GitHub Secrets and in `.env.example`. Ensure these are securely managed and backed up.

### Recovery Steps

In case of a major outage or data loss:

1.  **Assess Impact:** Determine the scope of the outage (application, S3, specific files).
2.  **Application Recovery:**
    *   If the application instances are down, rely on your orchestration platform (ECS/EKS) to restart them.
    *   If a new deployment caused the issue, perform an application rollback to a previous stable Docker image.
    *   If the entire environment is compromised, re-deploy the infrastructure using Terraform and then deploy the application.
3.  **S3 Data Recovery:**
    *   **Accidental Deletion/Overwrite:** Use S3 versioning to restore the desired object version.
    *   **Regional Outage (if CRR enabled):** Failover to the replicated bucket in the secondary region. Update application configuration to point to the new bucket.
    *   **Corrupted Data:** If data corruption is suspected, restore from the latest known good version using S3 versioning.
4.  **Post-Recovery Validation:**
    *   Perform health checks (`/health` endpoint).
    *   Run a subset of integration tests to confirm basic functionality.
    *   Monitor logs and metrics for any anomalies.

## 7. Maintenance & Scaling

*   **Regular Updates:** Keep Python dependencies, Docker base images, and AWS provider versions updated to benefit from security patches and new features.
*   **S3 Bucket Monitoring:** Monitor S3 bucket size, number of objects, and API requests via CloudWatch metrics.
*   **Application Scaling:**
    *   The FastAPI application is stateless (all state is in S3), making it highly scalable horizontally.
    *   **ECS/EKS:** Configure auto-scaling policies based on CPU utilization, memory, or request queue length.
*   **S3 Lifecycle Management:** Regularly review and adjust S3 lifecycle rules based on actual data retention requirements to optimize storage costs.

## 8. Security Best Practices

*   **Rotate Credentials:** Regularly rotate AWS IAM user access keys and API authentication tokens.
*   **Principle of Least Privilege:** Ensure all IAM roles/users have only the minimum necessary permissions.
*   **Network Security:**
    *   Deploy the application in a private subnet.
    *   Use Security Groups to restrict inbound traffic to only necessary ports (e.g., 8000 from a load balancer).
    *   Use VPC Endpoints for S3 to keep traffic within the AWS network, improving security and performance.
*   **HTTPS Everywhere:** Always serve the API over HTTPS in production using a load balancer with TLS termination.
*   **Input Validation:** FastAPI's Pydantic models provide strong input validation. Ensure all API inputs are validated.
*   **Dependency Scanning:** Integrate tools like `pip-audit` or `Snyk` into CI/CD to scan for known vulnerabilities in Python dependencies.
*   **Runtime Protection:** Consider using AWS WAF for web application firewall capabilities to protect against common web exploits.
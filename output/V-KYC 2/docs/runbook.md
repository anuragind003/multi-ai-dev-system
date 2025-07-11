# FastAPI AWS Monolithic Application - Runbook

This document serves as a runbook for operating, troubleshooting, and maintaining the FastAPI application deployed on AWS.

## Table of Contents

1.  [Overview](#1-overview)
2.  [Application Architecture](#2-application-architecture)
3.  [Deployment Process](#3-deployment-process)
4.  [Monitoring & Alerting](#4-monitoring--alerting)
    *   [Key Metrics](#key-metrics)
    *   [Alerts](#alerts)
5.  [Troubleshooting Guide](#5-troubleshooting-guide)
    *   [Application Issues](#application-issues)
    *   [Database Issues](#database-issues)
    *   [S3 Issues](#s3-issues)
    *   [EC2 Instance Issues](#ec2-instance-issues)
    *   [Network Connectivity Issues](#network-connectivity-issues)
    *   [Deployment/CI/CD Issues](#deploymentcicd-issues)
6.  [Backup & Recovery Procedures](#6-backup--recovery-procedures)
    *   [Database (RDS) Backup](#database-rds-backup)
    *   [S3 Bucket Backup](#s3-bucket-backup)
    *   [EC2 Instance Recovery](#ec2-instance-recovery)
    *   [Terraform State Recovery](#terraform-state-recovery)
7.  [Scaling Considerations](#7-scaling-considerations)
8.  [Security Best Practices](#8-security-best-practices)
9.  [Maintenance Tasks](#9-maintenance-tasks)

---

## 1. Overview

This runbook covers the operational aspects of the FastAPI application, which is a monolithic Python application containerized with Docker and deployed on an AWS EC2 instance. It uses AWS RDS for PostgreSQL and AWS S3 for file storage.

## 2. Application Architecture

*   **Application:** FastAPI (Python)
*   **Containerization:** Docker
*   **Compute:** AWS EC2 Instance (single instance for monolithic app)
*   **Database:** AWS RDS PostgreSQL
*   **Storage:** AWS S3 (for recordings/files)
*   **Networking:** AWS VPC, Public/Private Subnets, Security Groups, NAT Gateway, Internet Gateway
*   **CI/CD:** GitHub Actions
*   **Infrastructure as Code:** Terraform
*   **Monitoring:** Prometheus (local/on-EC2), Grafana (local/on-EC2), AWS CloudWatch

## 3. Deployment Process

The deployment is automated via GitHub Actions.

1.  **Code Commit:** Developer pushes code to the `main` branch or opens a Pull Request.
2.  **CI/CD Trigger:** GitHub Actions workflow (`.github/workflows/ci-cd.yml`) is triggered.
3.  **Build & Test Stage:**
    *   Linting (Flake8), Formatting (Black)
    *   Unit & Integration Tests (Pytest)
    *   Docker Image Build
    *   Security Scans (Trivy for Docker, Bandit for Python code)
    *   Performance Tests (Locust)
4.  **Deploy Stage (on `main` branch push):**
    *   AWS ECR Login.
    *   Docker image pushed to ECR.
    *   SSH into the EC2 instance.
    *   Pull the latest Docker image from ECR.
    *   Stop and remove the old container.
    *   Start a new container with the updated image and production environment variables.
    *   Basic health check after deployment.
5.  **Rollback:** If deployment fails, a basic rollback mechanism attempts to restart the previous stable image. Manual intervention might be required for complex rollbacks.

## 4. Monitoring & Alerting

### Key Metrics

*   **Application Metrics (from Prometheus/Grafana):**
    *   HTTP Request Rate (requests/sec)
    *   HTTP Request Latency (P50, P90, P99 percentiles)
    *   HTTP Status Codes (2xx, 4xx, 5xx rates)
    *   Application Memory/CPU Usage
    *   Database Connection Pool Usage
*   **EC2 Instance Metrics (from CloudWatch/Node Exporter):**
    *   CPU Utilization
    *   Memory Utilization (if CloudWatch agent installed)
    *   Disk I/O (Read/Write Bytes, Operations)
    *   Network I/O (In/Out Bytes, Packets)
    *   Disk Space Utilization
*   **RDS PostgreSQL Metrics (from CloudWatch):**
    *   CPU Utilization
    *   Database Connections
    *   Freeable Memory
    *   Disk Queue Depth
    *   Read/Write IOPS, Latency, Throughput
    *   Database Connections
*   **S3 Bucket Metrics (from CloudWatch):**
    *   Total Request Count
    *   Errors (4xx, 5xx)
    *   Bucket Size

### Alerts

Configure CloudWatch Alarms or Prometheus Alertmanager for the following:

*   **Application:**
    *   High 5xx error rate (>5% for 5 minutes)
    *   High P99 request latency (>500ms for 5 minutes)
    *   Application container not running/unhealthy
*   **EC2:**
    *   High CPU utilization (>80% for 15 minutes)
    *   Low Free Memory (<10% for 15 minutes)
    *   Low Disk Space (<10% free)
    *   Instance status check failed
*   **RDS:**
    *   High CPU utilization (>80% for 15 minutes)
    *   High Database Connections (>80% of max connections)
    *   Low Freeable Memory (<10% for 15 minutes)
    *   High Disk Queue Depth (>10 for 15 minutes)
*   **S3:**
    *   High number of 5xx errors on S3 bucket operations.

**Alerting Channels:** Integrate with PagerDuty, Slack, Email, etc.

## 5. Troubleshooting Guide

### Application Issues

*   **Symptom:** Application is unreachable or returning 5xx errors.
    *   **Check:**
        1.  **EC2 Instance Status:** Is the EC2 instance running? (AWS Console -> EC2 -> Instances)
        2.  **Docker Container Status:** SSH into EC2, run `docker ps`. Is `fastapi-app` container running and healthy?
        3.  **Container Logs:** `docker logs fastapi-app`. Look for Python tracebacks, database connection errors, or startup failures.
        4.  **Health Check Endpoint:** Try `curl http://localhost:8000/health` from within the EC2 instance.
        5.  **Resource Utilization:** Check EC2 CPU/Memory via CloudWatch. Is the instance overloaded?
    *   **Resolution:**
        *   Restart container: `docker restart fastapi-app`
        *   If logs show DB connection issues, check RDS status.
        *   If resource issues, consider scaling up EC2 instance type.

### Database Issues

*   **Symptom:** Application logs show database connection errors or slow queries.
    *   **Check:**
        1.  **RDS Instance Status:** Is the RDS instance `Available`? (AWS Console -> RDS -> Databases)
        2.  **RDS Metrics:** Check CloudWatch metrics for RDS (CPU, connections, disk I/O, freeable memory).
        3.  **Security Group:** Is the EC2 instance's security group allowed to connect to the RDS security group on port 5432?
        4.  **Database Credentials:** Are `PROD_DATABASE_URL` and other credentials correct and accessible to the application?
        5.  **Network ACLs/Route Tables:** Ensure private subnets have correct routing to NAT Gateway for outbound connections (e.g., to S3, if DB needs it).
    *   **Resolution:**
        *   If RDS is down, check AWS Service Health Dashboard.
        *   Optimize slow queries in application code.
        *   Scale up RDS instance type or storage.
        *   Verify network connectivity and security group rules.

### S3 Issues

*   **Symptom:** File uploads/downloads fail, application logs show S3 errors.
    *   **Check:**
        1.  **S3 Bucket Existence:** Does the bucket specified in `PROD_S3_BUCKET_NAME` exist? (AWS Console -> S3)
        2.  **IAM Permissions:** Does the EC2 instance's IAM role have `s3:PutObject`, `s3:GetObject`, `s3:ListBucket` permissions for the specific bucket?
        3.  **Network Connectivity:** Can the EC2 instance reach S3 endpoints? (S3 uses public endpoints, so NAT Gateway is needed for private subnets).
        4.  **S3 Metrics:** Check CloudWatch metrics for S3 bucket errors.
    *   **Resolution:**
        *   Verify IAM role policies.
        *   Check S3 bucket policy and public access block settings.
        *   Ensure NAT Gateway is functioning for private subnets.

### EC2 Instance Issues

*   **Symptom:** EC2 instance is unresponsive, status checks fail.
    *   **Check:**
        1.  **Instance Status Checks:** Are both System Status and Instance Status checks passing? (AWS Console -> EC2 -> Instances -> Status Checks)
        2.  **System Logs:** View EC2 system logs (AWS Console -> EC2 -> Instances -> Actions -> Monitor and troubleshoot -> Get system log).
        3.  **SSH Connectivity:** Can you SSH into the instance? If not, check security group, key pair, and network ACLs.
    *   **Resolution:**
        *   If status checks fail, try rebooting the instance.
        *   If reboot fails, consider stopping/starting (changes public IP) or terminating and recreating via Terraform.

### Network Connectivity Issues

*   **Symptom:** Application cannot reach DB, S3, or external services; external users cannot reach application.
    *   **Check:**
        1.  **Security Groups:** Verify ingress/egress rules for EC2 and RDS security groups.
        2.  **Network ACLs:** Check NACLs for subnets.
        3.  **Route Tables:** Ensure correct routes for public (IGW) and private (NAT Gateway) subnets.
        4.  **NAT Gateway:** Is the NAT Gateway `Available`? Is its EIP associated?
        5.  **Internet Gateway:** Is the IGW attached to the VPC?
    *   **Resolution:**
        *   Review and correct security group rules.
        *   Ensure NACLs allow necessary traffic.
        *   Verify route table associations and routes.

### Deployment/CI/CD Issues

*   **Symptom:** GitHub Actions workflow fails during build or deploy.
    *   **Check:**
        1.  **GitHub Actions Logs:** Review the detailed logs for the failed workflow run.
        2.  **Syntax Errors:** Check `.github/workflows/ci-cd.yml` for syntax errors.
        3.  **Secrets:** Are all required GitHub Secrets correctly configured and accessible? (e.g., `EC2_SSH_KEY`, `AWS_ACCESS_KEY_ID`).
        4.  **Permissions:** Does the AWS user/role used by GitHub Actions have necessary permissions for ECR, EC2 SSH, etc.?
        5.  **EC2 SSH Access:** Can you manually SSH into the EC2 instance using the key provided to GitHub Actions?
    *   **Resolution:**
        *   Fix code/configuration errors.
        *   Update GitHub Secrets.
        *   Adjust IAM permissions.
        *   Troubleshoot SSH connectivity manually.

## 6. Backup & Recovery Procedures

### Database (RDS) Backup

*   **Procedure:**
    1.  **Automated Snapshots:** RDS automatically creates daily snapshots. Configure retention period (e.g., 7-35 days) in RDS instance settings.
    2.  **Point-in-Time Recovery (PITR):** RDS enables PITR by default (if automated backups are on). You can restore to any point within the backup retention window.
    3.  **Manual Snapshots:** For critical events (e.g., before major schema changes), create a manual snapshot.
*   **Recovery:**
    1.  **Restore from Snapshot:** In AWS RDS Console, select the instance, then "Actions" -> "Restore to point in time" or "Restore snapshot".
    2.  **New Instance:** Restoring creates a *new* RDS instance. Update your application's `PROD_DATABASE_URL` to point to the new instance's endpoint.
    3.  **Data Validation:** Verify data integrity after restoration.

### S3 Bucket Backup

*   **Procedure:**
    1.  **Versioning:** S3 bucket has versioning enabled (`terraform/main.tf`). This automatically keeps multiple versions of an object, protecting against accidental overwrites or deletions.
    2.  **Cross-Region Replication (Optional):** For disaster recovery, configure S3 Cross-Region Replication to copy objects to a bucket in a different AWS region.
    3.  **Lifecycle Policies (Optional):** Define lifecycle rules to transition older versions to cheaper storage classes (e.g., S3 Glacier) or expire them.
*   **Recovery:**
    1.  **Restore Previous Version:** If an object is accidentally deleted or overwritten, you can restore a previous version from the S3 console or via AWS CLI/SDK.
    2.  **Replication Failover:** If using cross-region replication, update application configuration to point to the replicated bucket in the secondary region.

### EC2 Instance Recovery

*   **Procedure:**
    1.  The EC2 instance is considered ephemeral. Its state is managed by Terraform and Docker.
    2.  **AMI Creation (Optional):** For faster recovery of a pre-configured instance, create an AMI of the running EC2 instance periodically.
*   **Recovery:**
    1.  **Terraform Re-apply:** If the EC2 instance fails, `terraform apply` will recreate it based on the `main.tf` definition. The `user_data` script will re-install Docker.
    2.  **Application Deployment:** The CI/CD pipeline can then be triggered to deploy the latest Docker image to the new EC2 instance.
    3.  **Data:** Application data is in RDS and S3, so no data loss on EC2 recreation.

### Terraform State Recovery

*   **Procedure:**
    1.  **Remote State:** The Terraform state should be stored remotely (e.g., S3 backend with DynamoDB locking) to prevent loss and enable collaboration.
    2.  **State Backups:** S3 bucket versioning for the state file provides a history of state changes.
*   **Recovery:**
    1.  **Restore from S3 Version:** If the state file is corrupted, restore a previous version from the S3 bucket.
    2.  **`terraform state pull` / `push`:** Use these commands to manually manage state if needed.
    3.  **`terraform import` (Last Resort):** If state is completely lost, you can import existing AWS resources into a new Terraform state, but this is complex and error-prone.

## 7. Scaling Considerations

*   **Vertical Scaling (EC2/RDS):** Increase instance type (CPU, RAM) for EC2 and RDS. This is the simplest but has limits.
*   **Horizontal Scaling (Application):**
    *   **Multiple EC2 Instances:** Deploy multiple EC2 instances behind an AWS Application Load Balancer (ALB). This requires configuring the ALB, target groups, and potentially an Auto Scaling Group.
    *   **Container Orchestration:** Migrate from a single EC2 instance to AWS ECS (Elastic Container Service) or EKS (Elastic Kubernetes Service) for robust container orchestration, auto-scaling, and service discovery. This is the recommended path for true horizontal scalability.
*   **Database Scaling:**
    *   **RDS Read Replicas:** For read-heavy workloads, add RDS Read Replicas to offload read traffic.
    *   **Sharding/Clustering:** For extreme scale, consider database sharding or more advanced clustering solutions (more complex).
*   **S3 Scaling:** S3 is highly scalable by nature and handles large volumes of data and requests automatically.

## 8. Security Best Practices

*   **Least Privilege:** Ensure IAM roles and policies grant only the necessary permissions.
*   **Network Segmentation:** Use private subnets for databases and internal services.
*   **Security Group Hardening:** Restrict SSH access to specific IP ranges. Only open necessary application ports (80/443).
*   **HTTPS Everywhere:** Use an ALB with ACM for SSL termination and enforce HTTPS for all public traffic.
*   **Secrets Management:** Use AWS Secrets Manager or SSM Parameter Store for all sensitive credentials in production.
*   **Regular Patching:** Keep EC2 AMIs, Docker images, and application dependencies updated.
*   **Vulnerability Scanning:** Continue using Trivy and Bandit in CI/CD. Consider continuous scanning tools.
*   **Logging & Auditing:** Enable CloudTrail for API activity logging and CloudWatch Logs for application logs.

## 9. Maintenance Tasks

*   **Regular Updates:** Periodically update base images (Python, Alpine), application dependencies (via `poetry update`), and system packages on EC2.
*   **Log Review:** Regularly review CloudWatch Logs for application errors, warnings, and unusual activity.
*   **Metric Review:** Monitor Grafana dashboards and CloudWatch metrics for performance trends and potential bottlenecks.
*   **Cost Optimization:** Review AWS costs regularly. Consider reserved instances or savings plans for stable workloads.
*   **Terraform Drift Detection:** Periodically run `terraform plan` to detect manual changes to infrastructure that are not reflected in code.
*   **Backup Verification:** Periodically test database restores and S3 object recovery to ensure backups are valid.
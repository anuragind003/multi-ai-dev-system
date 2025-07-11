# Backup and Recovery Procedures for FastAPI Monolithic Application

This document outlines the backup strategies and recovery procedures for the FastAPI monolithic application deployed on AWS EC2. A robust backup and recovery plan is crucial for disaster preparedness and business continuity.

## Table of Contents
1.  [Recovery Point Objective (RPO) & Recovery Time Objective (RTO)](#1-recovery-point-objective-rpo--recovery-time-objective-rto)
2.  [Backup Strategy](#2-backup-strategy)
    *   [2.1 Database Backup (PostgreSQL)](#21-database-backup-postgresql)
    *   [2.2 Application Code and Configuration](#22-application-code-and-configuration)
    *   [2.3 EC2 Instance State](#23-ec2-instance-state)
3.  [Recovery Procedures](#3-recovery-procedures)
    *   [3.1 Database Recovery](#31-database-recovery)
    *   [3.2 Application Recovery (New EC2 Instance)](#32-application-recovery-new-ec2-instance)
    *   [3.3 Application Recovery (Existing EC2 Instance)](#33-application-recovery-existing-ec2-instance)
4.  [Testing Backups and Recovery](#4-testing-backups-and-recovery)
5.  [Monitoring Backups](#5-monitoring-backups)

---

## 1. Recovery Point Objective (RPO) & Recovery Time Objective (RTO)

*   **RPO (Recovery Point Objective):** The maximum acceptable amount of data loss measured in time.
    *   **Target:** 24 hours (for database, meaning we can lose up to 24 hours of data).
*   **RTO (Recovery Time Objective):** The maximum acceptable downtime after a disaster.
    *   **Target:** 4 hours (for application restoration).

These targets should be reviewed and adjusted based on business requirements.

## 2. Backup Strategy

### 2.1 Database Backup (PostgreSQL)

Assuming an external PostgreSQL database (e.g., AWS RDS).

*   **Automated Snapshots (AWS RDS):**
    *   **Method:** AWS RDS automatically creates and stores automated backups (snapshots) of your DB instance.
    *   **Configuration:**
        *   **Backup Retention Period:** Configure RDS to retain snapshots for at least 7 days (or more, based on RPO).
        *   **Backup Window:** Define a daily backup window during low traffic periods.
    *   **Benefits:** Point-in-time recovery to any second within the retention period.
*   **Manual Snapshots (AWS RDS):**
    *   **Method:** Create manual snapshots before major changes (e.g., schema migrations, application deployments).
    *   **Retention:** Manual snapshots are retained indefinitely until you delete them.
*   **Logical Backups (pg_dump):**
    *   **Method:** For additional safety or specific use cases (e.g., cross-region restore, data migration), perform `pg_dump` of critical schemas/tables.
    *   **Frequency:** Daily/Weekly, stored in an S3 bucket with versioning and lifecycle policies.
    *   **Example (from EC2 or a dedicated backup server):**
        ```bash
        PGPASSWORD="your_db_password" pg_dump -h <DB_HOST> -U <DB_USER> -d <DB_NAME> > /tmp/db_backup_$(date +%Y%m%d%H%M%S).sql
        aws s3 cp /tmp/db_backup_*.sql s3://your-backup-bucket/db-backups/
        rm /tmp/db_backup_*.sql
        ```
        Automate this with a cron job.

### 2.2 Application Code and Configuration

*   **Application Code:**
    *   **Method:** All application code is stored in a Git repository (GitLab).
    *   **Backup:** Git itself serves as the primary backup. Ensure your GitLab instance (if self-hosted) is backed up, or rely on GitLab.com's redundancy.
    *   **Recovery:** Clone the repository.
*   **Application Configuration (`.env`):**
    *   **Method:** Sensitive configurations are managed via GitLab CI/CD variables.
    *   **Backup:** These are backed up as part of GitLab's internal backup procedures.
    *   **Recovery:** Re-enter or restore from GitLab's configuration. For production, use a secrets manager like AWS Secrets Manager, which has its own backup/replication.
*   **Terraform State File (`terraform.tfstate`):**
    *   **Method:** The Terraform state file is crucial for managing infrastructure. It should be stored remotely in an S3 bucket with versioning enabled.
    *   **Configuration (in `terraform/main.tf`):**
        ```terraform
        terraform {
          backend "s3" {
            bucket = "your-terraform-state-bucket"
            key    = "fastapi-monolith/terraform.tfstate"
            region = "us-east-1"
            encrypt = true
            dynamodb_table = "your-terraform-lock-table" # For state locking
          }
        }
        ```
    *   **Backup:** S3 bucket versioning provides automatic backups of state file changes.
    *   **Recovery:** Terraform can restore from a specific version of the state file in S3.

### 2.3 EC2 Instance State

*   **AMI (Amazon Machine Image):**
    *   **Method:** Create AMIs of your EC2 instance periodically, especially after major OS updates or software installations (e.g., Docker, Docker Compose).
    *   **Frequency:** Monthly or after significant changes to the base OS/software setup.
    *   **Benefits:** Allows you to quickly launch a new EC2 instance with the same base configuration.
    *   **Automation:** Use AWS Lambda or CloudWatch Events to automate AMI creation.
*   **EBS Snapshots:**
    *   **Method:** EBS volumes (which your EC2 instance uses) can be snapshotted.
    *   **Frequency:** Daily.
    *   **Benefits:** Point-in-time backup of the entire root volume.
    *   **Automation:** Use AWS Backup or Lifecycle Manager for EBS snapshots.

## 3. Recovery Procedures

### 3.1 Database Recovery

*   **From Automated/Manual RDS Snapshots:**
    1.  Go to AWS RDS Console -> Databases.
    2.  Select your DB instance.
    3.  Under "Actions", choose "Restore to point in time" or "Restore snapshot".
    4.  Specify a new DB instance identifier (e.g., `mydatabase-restored`).
    5.  Once restored, update your application's `DATABASE_URL` to point to the new DB instance.
*   **From `pg_dump` files:**
    1.  Provision a new PostgreSQL database instance.
    2.  Copy the `pg_dump` file from S3 to a server that can connect to the new DB.
    3.  Restore the database:
        ```bash
        psql -h <NEW_DB_HOST> -U <NEW_DB_USER> -d <NEW_DB_NAME> < db_backup.sql
        ```
    4.  Update application's `DATABASE_URL`.

### 3.2 Application Recovery (New EC2 Instance)

This procedure is for a complete EC2 instance failure or region-wide disaster.

1.  **Restore Terraform State:** Ensure your `terraform.tfstate` is accessible in S3.
2.  **Provision New EC2 Instance:**
    *   Run `terraform apply` from the `terraform/` directory. This will provision a new EC2 instance with Docker and Docker Compose installed via `user_data`.
    *   If you have a recent AMI, you can modify `main.tf` to use that AMI instead of the base Ubuntu AMI for faster recovery of the base OS setup.
3.  **Update CI/CD Variables:**
    *   After `terraform apply`, get the new `EC2_INSTANCE_IP` from Terraform outputs.
    *   Update the `EC2_INSTANCE_IP` CI/CD variable in GitLab.
4.  **Deploy Application:**
    *   Trigger the `deploy_application` job in GitLab CI/CD (manual job). This will pull the latest Docker image and run it on the new EC2 instance.
5.  **Verify:** Perform health checks and basic functionality tests.
6.  **DNS Update:** If using a custom domain, update your DNS records to point to the new EC2 instance's IP or a new Load Balancer.

### 3.3 Application Recovery (Existing EC2 Instance)

This procedure is for application-level failures on an existing, healthy EC2 instance.

1.  **Rollback to Previous Version:**
    *   If a recent deployment caused the issue, trigger the `rollback_application` job in GitLab CI/CD. This will revert the application to the previously deployed Docker image.
2.  **Restart Application Container:**
    *   If the container crashed, SSH into the EC2 instance and run `docker restart fastapi-app`.
3.  **Manual Redeploy:**
    *   If automated rollback/restart fails, manually pull and run a known good image:
        ```bash
        ssh -i /path/to/key.pem ubuntu@<EC2_INSTANCE_IP> << EOF
          docker pull <CI_REGISTRY_IMAGE>:<KNOWN_GOOD_SHA>
          docker stop fastapi-app || true
          docker rm fastapi-app || true
          docker run -d --name fastapi-app -p 8000:8000 --restart always <CI_REGISTRY_IMAGE>:<KNOWN_GOOD_SHA>
        EOF
        ```

## 4. Testing Backups and Recovery

*   **Regular Drills:** Conduct periodic (e.g., quarterly) disaster recovery drills.
    *   Simulate a database failure and restore from a snapshot.
    *   Simulate an EC2 instance failure and perform a full application recovery to a new instance.
*   **Automated Checks:** Implement automated checks to verify backup integrity (e.g., check if RDS snapshots are being created, if S3 backups exist).

## 5. Monitoring Backups

*   **AWS CloudWatch:** Monitor RDS snapshot creation events, EBS snapshot completion, and S3 bucket activity.
*   **Alerting:** Set up alerts for backup failures or unusually long backup times.

By adhering to these backup and recovery procedures, you can minimize data loss and downtime in the event of a disaster.
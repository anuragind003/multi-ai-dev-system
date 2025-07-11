# Backup and Recovery Procedures

This document outlines the backup and recovery strategies for the FastAPI Backend and Next.js Frontend application. A robust backup and recovery plan is crucial for business continuity and disaster preparedness.

## 1. Scope

This document covers:
*   Application code and configuration.
*   Container images.
*   Monitoring data (Prometheus, Grafana).
*   (Placeholder for Database data - if a database were integrated).

## 2. Backup Strategy

### 2.1. Application Code and Configuration

*   **What to backup:** All source code, Dockerfiles, Docker Compose files, Kubernetes manifests, Nginx configurations, and `.env.example` templates.
*   **Method:** All application code and configuration files are stored in a Git repository (e.g., GitHub). This repository serves as the primary backup for the code.
*   **Frequency:** Every commit/push to the repository.
*   **Retention:** Git history provides full versioning.

### 2.2. Container Images

*   **What to backup:** Built Docker images for the FastAPI backend and Next.js frontend.
*   **Method:** Images are pushed to a Docker Registry (e.g., Docker Hub, Google Container Registry, AWS ECR) as part of the CI/CD pipeline. The registry itself provides storage and versioning.
*   **Frequency:** On every successful build in the CI/CD pipeline (typically on `main` branch pushes).
*   **Retention:** Registry policies (e.g., retain last N images, or images tagged with specific versions).

### 2.3. Monitoring Data (Prometheus & Grafana)

#### 2.3.1. Prometheus Data (Time Series Database)

*   **What to backup:** The Prometheus Time Series Database (TSDB) data, which contains all collected metrics.
*   **Method (Docker Compose):**
    *   Prometheus uses a Docker volume (`prometheus_data`) for persistence.
    *   To back up, stop the Prometheus container, then copy the contents of the Docker volume to a secure location.
    *   Example (Linux/macOS):
        ```bash
        docker compose -f docker-compose.prod.yml stop prometheus
        # Find the volume path (replace <volume_name> with the actual volume name, e.g., your-repo-name_prometheus_data)
        docker volume inspect <volume_name> | grep Mountpoint
        # Copy the data
        sudo cp -R <mount_point>/prometheus /path/to/your/backup/location/prometheus_backup_$(date +%Y%m%d%H%M%S)
        docker compose -f docker-compose.prod.yml start prometheus
        ```
*   **Method (Kubernetes):**
    *   Prometheus deployments in Kubernetes typically use Persistent Volumes (PVs) and Persistent Volume Claims (PVCs).
    *   Leverage your cloud provider's snapshotting capabilities for PVs (e.g., AWS EBS snapshots, GCP Persistent Disk snapshots).
    *   Alternatively, use tools like Velero for Kubernetes backup and restore.
*   **Frequency:** Daily snapshots/backups recommended for critical metrics.
*   **Retention:** Based on organizational policy (e.g., 7 daily, 4 weekly, 12 monthly).

#### 2.3.2. Grafana Configuration and Dashboards

*   **What to backup:** Grafana dashboards, datasources, and user configurations.
*   **Method:**
    *   **Dashboards & Datasources:** In this setup, dashboards and datasources are provisioned from files (`grafana/provisioning/`). These files are version-controlled in Git, so they are implicitly backed up.
    *   **Grafana Internal Database:** Grafana stores users, alerts, and other settings in an internal SQLite database (by default) or an external database. This is persisted via the `grafana_data` Docker volume or a Kubernetes PV. Backup this volume similar to Prometheus data.
*   **Frequency:** As per Git commits for provisioning files; daily for internal database.
*   **Retention:** Git history for files; based on organizational policy for internal database.

### 2.4. Database Data (Placeholder)

*   **What to backup:** All application data stored in the database (e.g., PostgreSQL, MySQL, MongoDB).
*   **Method:**
    *   **Logical Backups:** Use database-specific tools like `pg_dump`, `mysqldump`, `mongodump` to create logical backups (SQL dumps, BSON dumps).
    *   **Physical Backups:** For larger databases, consider physical backups (copying data files) or leveraging cloud provider database services (RDS, Cloud SQL) with automated backups and point-in-time recovery.
*   **Frequency:** Daily full backups, hourly incremental/WAL archiving.
*   **Retention:** Based on RPO (Recovery Point Objective) and RTO (Recovery Time Objective) requirements.

## 3. Recovery Strategy

### 3.1. Application Code and Configuration Recovery

*   **Procedure:**
    1.  Clone the Git repository: `git clone <repo-url>`
    2.  Checkout the desired commit/tag: `git checkout <commit-hash-or-tag>`
    3.  Redeploy the application using Docker Compose or Kubernetes manifests.

### 3.2. Container Image Recovery

*   **Procedure:**
    1.  Pull the desired image version from the Docker Registry: `docker pull <image-name>:<tag>`
    2.  Update your Docker Compose file or Kubernetes manifest to use the recovered image tag.
    3.  Redeploy the service.

### 3.3. Monitoring Data Recovery

#### 3.3.1. Prometheus Data Recovery

*   **Procedure (Docker Compose):**
    1.  Stop the Prometheus container: `docker compose -f docker-compose.prod.yml stop prometheus`
    2.  Clear the existing Prometheus data volume (or create a new one).
    3.  Copy the backed-up TSDB data into the Prometheus data volume.
    4.  Start the Prometheus container: `docker compose -f docker-compose.prod.yml start prometheus`
*   **Procedure (Kubernetes):**
    1.  Restore the Persistent Volume from a snapshot or using Velero.
    2.  Ensure the Prometheus pod is restarted to pick up the restored data.

#### 3.3.2. Grafana Configuration and Dashboards Recovery

*   **Procedure:**
    1.  **Provisioning Files:** Ensure the `grafana/provisioning/` directory contains the correct files from Git. Grafana will re-provision datasources and dashboards on startup.
    2.  **Internal Database:** Restore the `grafana_data` volume from backup, similar to Prometheus.

### 3.4. Database Data Recovery (Placeholder)

*   **Procedure:**
    1.  Provision a new database instance if the original is irrecoverable.
    2.  Restore the latest full backup.
    3.  Apply incremental backups/transaction logs to achieve the desired RPO.
    4.  Verify data consistency and integrity.
    5.  Update application configuration to point to the recovered database.

## 4. Disaster Recovery (Full System Outage)

In the event of a complete data center or cloud region failure:

1.  **Provision New Infrastructure:** Use Infrastructure as Code (e.g., Terraform, CloudFormation) to provision a new environment (VMs, Kubernetes cluster, networking) in a different region or data center.
2.  **Deploy Application:** Use the CI/CD pipeline to deploy the latest stable version of the application from the Git repository to the new infrastructure.
3.  **Restore Data:**
    *   Restore the database from the latest off-site backup.
    *   Restore any other persistent data volumes.
    *   Restore monitoring data if necessary.
4.  **DNS Update:** Update DNS records to point to the new application endpoints.
5.  **Verification:** Thoroughly test all application functionalities, integrations, and monitoring.

## 5. Regular Testing of Backups

*   **Frequency:** At least quarterly, or after significant architectural changes.
*   **Method:** Perform a full recovery drill in a separate, isolated environment. This includes restoring all components (code, data, configuration) and verifying application functionality.
*   **Documentation:** Update this document with any lessons learned or improvements identified during testing.

This document serves as a living guide. It should be reviewed and updated regularly to reflect changes in the application, infrastructure, and business requirements.
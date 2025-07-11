#!/bin/bash
# scripts/backup_elk.sh
# Script to perform a snapshot backup of Elasticsearch data.
# This script assumes Elasticsearch is running and accessible.
# For production, ensure proper authentication, error handling, and offsite storage.

# --- Configuration ---
ELASTICSEARCH_HOST="localhost:9200" # Or the IP/hostname of your Elasticsearch instance
ELASTIC_USER="elastic"
ELASTIC_PASSWORD="${ELASTIC_PASSWORD:-changeme_elastic_password_123}" # Use environment variable or default
SNAPSHOT_REPO_NAME="my_backup_repo"
SNAPSHOT_NAME="fastapi_elk_snapshot_$(date +%Y%m%d%H%M%S)"
BACKUP_DIR="/usr/share/elasticsearch/data/backups" # This path must be mounted as a volume in ES container

# --- Functions ---
log_info() {
  echo "[INFO] $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_error() {
  echo "[ERROR] $(date '+%Y-%m-%d %H:%M:%S') $1" >&2
  exit 1
}

# --- Main Script ---

log_info "Starting Elasticsearch snapshot backup..."

# 1. Check if Elasticsearch is reachable
log_info "Checking Elasticsearch connectivity..."
curl -s -u "${ELASTIC_USER}:${ELASTIC_PASSWORD}" "http://${ELASTICSEARCH_HOST}/_cluster/health?wait_for_status=yellow&timeout=30s" > /dev/null
if [ $? -ne 0 ]; then
  log_error "Elasticsearch is not reachable or healthy. Aborting backup."
fi
log_info "Elasticsearch is reachable."

# 2. Register a snapshot repository (if not already registered)
# For a file system repository, the path must be configured in elasticsearch.yml
# (e.g., path.repo: ["/usr/share/elasticsearch/data/backups"]) and mounted as a volume.
log_info "Checking/Registering snapshot repository: ${SNAPSHOT_REPO_NAME}"
REPO_STATUS=$(curl -s -u "${ELASTIC_USER}:${ELASTIC_PASSWORD}" -X GET "http://${ELASTICSEARCH_HOST}/_snapshot/${SNAPSHOT_REPO_NAME}")

if echo "${REPO_STATUS}" | grep -q "repository_not_found"; then
  log_info "Repository '${SNAPSHOT_REPO_NAME}' not found. Creating it..."
  CREATE_REPO_RESPONSE=$(curl -s -u "${ELASTIC_USER}:${ELASTIC_PASSWORD}" -X PUT "http://${ELASTICSEARCH_HOST}/_snapshot/${SNAPSHOT_REPO_NAME}" -H 'Content-Type: application/json' -d "{
    \"type\": \"fs\",
    \"settings\": {
      \"location\": \"${BACKUP_DIR}\"
    }
  }")
  if echo "${CREATE_REPO_RESPONSE}" | grep -q "error"; then
    log_error "Failed to create snapshot repository: ${CREATE_REPO_RESPONSE}"
  else
    log_info "Snapshot repository '${SNAPSHOT_REPO_NAME}' created successfully."
  fi
else
  log_info "Snapshot repository '${SNAPSHOT_REPO_NAME}' already exists."
fi

# 3. Create the snapshot
log_info "Creating snapshot '${SNAPSHOT_NAME}' in repository '${SNAPSHOT_REPO_NAME}'..."
SNAPSHOT_RESPONSE=$(curl -s -u "${ELASTIC_USER}:${ELASTIC_PASSWORD}" -X PUT "http://${ELASTICSEARCH_HOST}/_snapshot/${SNAPSHOT_REPO_NAME}/${SNAPSHOT_NAME}?wait_for_completion=true")

if echo "${SNAPSHOT_RESPONSE}" | grep -q "\"failures\":\[\]"; then
  log_info "Snapshot '${SNAPSHOT_NAME}' created successfully."
  log_info "Snapshot details: ${SNAPSHOT_RESPONSE}"
else
  log_error "Failed to create snapshot: ${SNAPSHOT_RESPONSE}"
fi

log_info "Elasticsearch snapshot backup completed."

# --- Recovery Procedure (Manual Steps) ---
# To restore a snapshot:
# 1. Stop Logstash and Kibana.
# 2. Ensure Elasticsearch is running (preferably in a new cluster or empty data directory).
# 3. Register the same snapshot repository (if not already).
#    curl -X PUT "http://localhost:9200/_snapshot/my_backup_repo" -H 'Content-Type: application/json' -d'{"type": "fs", "settings": {"location": "/usr/share/elasticsearch/data/backups"}}'
# 4. Close the indices you want to restore (if they exist and are open).
#    curl -X POST "http://localhost:9200/your_index_name/_close"
# 5. Restore the snapshot.
#    curl -X POST "http://localhost:9200/_snapshot/my_backup_repo/fastapi_elk_snapshot_YYYYMMDDHHMMSS/_restore" -H 'Content-Type: application/json' -d'{"indices": ["fastapi-logs-*"], "ignore_unavailable": true, "include_global_state": false}'
# 6. Open the restored indices.
#    curl -X POST "http://localhost:9200/your_index_name/_open"
# 7. Start Logstash and Kibana.

# For production, consider using S3 or GCS repositories for offsite storage.
# Example for S3:
# PUT /_snapshot/my_s3_repository
# {
#   "type": "s3",
#   "settings": {
#     "bucket": "my-es-backup-bucket",
#     "region": "us-east-1",
#     "base_path": "snapshots/"
#   }
# }
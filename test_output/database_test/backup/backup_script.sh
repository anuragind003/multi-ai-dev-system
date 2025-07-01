#!/bin/bash
# Backup script for PostgreSQL

BACKUP_DIR="/path/to/backups"
DATABASE="your_database_name"
USERNAME="your_username"
DATE=$(date +%Y-%m-%d_%H-%M-%S)

pg_dump -U $USERNAME -d $DATABASE -Fc -f $BACKUP_DIR/$DATABASE-$DATE.dump
# Add cross-region replication logic here if needed
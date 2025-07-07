#!/bin/bash
# Backup script (example using pg_dump)
pg_dump -h localhost -p 5432 -U postgres -Fc mydatabase > /path/to/backup/mydatabase.dump
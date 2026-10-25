#!/usr/bin/env bash
# ==============================================================================
# Smart Memo SaaS — Automated Production Database Backup Script
# Performs compressed pg_dump with SHA256 integrity verification & 30-day pruning.
# ==============================================================================

set -euo pipefail

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="${BACKUP_DIR:-./backups/database}"
DB_NAME="${DB_NAME:-smart_memo}"
DB_USER="${DB_USER:-smart_memo_user}"
DB_HOST="${DB_HOST:-127.0.0.1}"
DB_PORT="${DB_PORT:-5431}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"

mkdir -p "${BACKUP_DIR}"

BACKUP_FILE="${BACKUP_DIR}/smart_memo_backup_${TIMESTAMP}.sql.gz"
CHECKSUM_FILE="${BACKUP_FILE}.sha256"

echo "=================================================="
echo "Starting database backup for '${DB_NAME}'..."
echo "Host: ${DB_HOST}:${DB_PORT} | User: ${DB_USER}"
echo "Target: ${BACKUP_FILE}"
echo "=================================================="

# Export PGPASSWORD if DB_PASSWORD is set
if [ -n "${DB_PASSWORD:-}" ]; then
    export PGPASSWORD="${DB_PASSWORD}"
fi

# Execute pg_dump and pipe through gzip
pg_dump -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" --clean --if-exists --no-owner --no-privileges | gzip -9 > "${BACKUP_FILE}"

# Generate SHA256 checksum for backup integrity verification
sha256sum "${BACKUP_FILE}" > "${CHECKSUM_FILE}"

FILE_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)

echo " Backup completed successfully!"
echo "Size: ${FILE_SIZE}"
echo "SHA256: $(cat "${CHECKSUM_FILE}")"

# Prune backups older than RETENTION_DAYS
echo "Pruning database backups older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" -type f -name "smart_memo_backup_*.sql.gz*" -mtime +"${RETENTION_DAYS}" -delete || true

echo "Backup workflow finished."

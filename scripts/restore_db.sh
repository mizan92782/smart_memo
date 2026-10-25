#!/usr/bin/env bash
# ==============================================================================
# Smart Memo SaaS — Safe Production Database Restore Script
# Restores a compressed SQL dump into PostgreSQL after checksum verification.
# Usage: ./scripts/restore_db.sh <path_to_backup_file.sql.gz>
# ==============================================================================

set -euo pipefail

if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <path_to_backup_file.sql.gz>"
    exit 1
fi

BACKUP_FILE="$1"
DB_NAME="${DB_NAME:-smart_memo}"
DB_USER="${DB_USER:-smart_memo_user}"
DB_HOST="${DB_HOST:-127.0.0.1}"
DB_PORT="${DB_PORT:-5431}"

if [ ! -f "${BACKUP_FILE}" ]; then
    echo "Error: Backup file '${BACKUP_FILE}' not found."
    exit 1
fi

# Verify checksum if .sha256 exists
CHECKSUM_FILE="${BACKUP_FILE}.sha256"
if [ -f "${CHECKSUM_FILE}" ]; then
    echo "Verifying SHA256 checksum..."
    sha256sum -c "${CHECKSUM_FILE}"
    echo "Checksum verified."
else
    echo "Warning: No .sha256 file found. Proceeding with restore..."
fi

# Export PGPASSWORD if DB_PASSWORD is set
if [ -n "${DB_PASSWORD:-}" ]; then
    export PGPASSWORD="${DB_PASSWORD}"
fi

echo "=================================================="
echo "Restoring database '${DB_NAME}' from '${BACKUP_FILE}'..."
echo "Host: ${DB_HOST}:${DB_PORT} | User: ${DB_USER}"
echo "=================================================="

# Decompress and feed to psql
gunzip -c "${BACKUP_FILE}" | psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}"

echo "Database restoration completed successfully!"

#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="/home/hl-lenovo/projects/nasahub"
ENV_FILE="${ROOT_DIR}/infra/.env"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing environment file: ${ENV_FILE}" >&2
  exit 1
fi

set -a
source "${ENV_FILE}"
set +a

BACKUP_ROOT="${BACKUP_ROOT:-${ROOT_DIR}/backups/postgres}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
TIMESTAMP="$(date -u +"%Y%m%dT%H%M%SZ")"
BACKUP_DIR="${BACKUP_ROOT}/${TIMESTAMP}"
BACKUP_FILE="${BACKUP_DIR}/nasahub_${TIMESTAMP}.dump"
METADATA_FILE="${BACKUP_DIR}/metadata.json"

mkdir -p "${BACKUP_DIR}"

echo "Creating PostgreSQL backup at ${BACKUP_FILE}"

/usr/bin/docker exec \
  -e "PGPASSWORD=${POSTGRES_PASSWORD}" \
  nasahub-postgres \
  pg_dump \
    --username="${POSTGRES_USER}" \
    --dbname="${POSTGRES_DB}" \
    --format=custom \
    --no-owner \
    --no-privileges \
    > "${BACKUP_FILE}"

cat > "${METADATA_FILE}" <<EOF
{
  "created_at_utc": "${TIMESTAMP}",
  "database": "${POSTGRES_DB}",
  "container": "nasahub-postgres",
  "format": "pg_dump custom",
  "backup_file": "${BACKUP_FILE}"
}
EOF

find "${BACKUP_ROOT}" -mindepth 1 -maxdepth 1 -type d -mtime +"${BACKUP_RETENTION_DAYS}" -exec rm -rf {} +

echo "Backup complete."
echo "Backup directory: ${BACKUP_DIR}"

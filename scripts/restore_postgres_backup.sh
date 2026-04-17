#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 /absolute/path/to/backup.dump" >&2
  exit 1
fi

ROOT_DIR="/home/hl-lenovo/projects/nasahub"
ENV_FILE="${ROOT_DIR}/infra/.env"
BACKUP_FILE="$1"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing environment file: ${ENV_FILE}" >&2
  exit 1
fi

if [[ ! -f "${BACKUP_FILE}" ]]; then
  echo "Backup file not found: ${BACKUP_FILE}" >&2
  exit 1
fi

set -a
source "${ENV_FILE}"
set +a

echo "Restore target database: ${POSTGRES_DB}"
echo "Backup file: ${BACKUP_FILE}"
echo
echo "WARNING: this will DROP and recreate the public schemas inside the running NASAHub database."
echo "Only continue if you are sure this is the restore point you want."
read -r -p "Type RESTORE to continue: " CONFIRMATION

if [[ "${CONFIRMATION}" != "RESTORE" ]]; then
  echo "Restore cancelled."
  exit 1
fi

cat "${BACKUP_FILE}" | /usr/bin/docker exec -i \
  -e "PGPASSWORD=${POSTGRES_PASSWORD}" \
  nasahub-postgres \
  pg_restore \
    --username="${POSTGRES_USER}" \
    --dbname="${POSTGRES_DB}" \
    --clean \
    --if-exists \
    --no-owner \
    --no-privileges

echo "Restore complete."

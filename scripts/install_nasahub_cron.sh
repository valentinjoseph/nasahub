#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="/home/hl-lenovo/projects/nasahub"
CRON_TEMPLATE="${ROOT_DIR}/infra/nasahub.crontab"
TMP_CRON="$(mktemp)"
CURRENT_CRON="$(mktemp)"

cleanup() {
  rm -f "${TMP_CRON}" "${CURRENT_CRON}"
}
trap cleanup EXIT

if [[ ! -f "${CRON_TEMPLATE}" ]]; then
  echo "Missing cron template: ${CRON_TEMPLATE}" >&2
  exit 1
fi

if crontab -l > "${CURRENT_CRON}" 2>/dev/null; then
  :
else
  : > "${CURRENT_CRON}"
fi

awk '
  BEGIN {skip=0}
  /^# NASAHub managed jobs begin$/ {skip=1; next}
  /^# NASAHub managed jobs end$/ {skip=0; next}
  skip==0 {print}
' "${CURRENT_CRON}" > "${TMP_CRON}"

{
  cat "${TMP_CRON}"
  echo "# NASAHub managed jobs begin"
  cat "${CRON_TEMPLATE}"
  echo "# NASAHub managed jobs end"
} | crontab -

echo "NASAHub cron jobs installed."
crontab -l

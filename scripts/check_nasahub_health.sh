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

MONITOR_PUBLIC_BASE_URL="${MONITOR_PUBLIC_BASE_URL:-https://${NASAHUB_PUBLIC_HOST}}"
MONITOR_LOCAL_READY_URL="${MONITOR_LOCAL_READY_URL:-http://127.0.0.1:8000/health/ready}"
MONITOR_PUBLIC_READY_URL="${MONITOR_PUBLIC_READY_URL:-${MONITOR_PUBLIC_BASE_URL}/health/ready}"
MONITOR_TIMEOUT_SECONDS="${MONITOR_TIMEOUT_SECONDS:-15}"
MONITOR_BACKUP_MAX_AGE_HOURS="${MONITOR_BACKUP_MAX_AGE_HOURS:-30}"
MONITOR_CERT_MIN_DAYS="${MONITOR_CERT_MIN_DAYS:-21}"
MONITOR_RUN_MAX_AGE_HOURS="${MONITOR_RUN_MAX_AGE_HOURS:-48}"
MONITOR_RUN_MAX_AGE_HOURS_EONET_CATEGORIES="${MONITOR_RUN_MAX_AGE_HOURS_EONET_CATEGORIES:-24}"
MONITOR_RUN_MAX_AGE_HOURS_EONET_EVENTS="${MONITOR_RUN_MAX_AGE_HOURS_EONET_EVENTS:-24}"
MONITOR_RUN_MAX_AGE_HOURS_EONET_LAYERS="${MONITOR_RUN_MAX_AGE_HOURS_EONET_LAYERS:-24}"
MONITOR_RUN_MAX_AGE_HOURS_EONET_SOURCES="${MONITOR_RUN_MAX_AGE_HOURS_EONET_SOURCES:-24}"
MONITOR_RUN_MAX_AGE_HOURS_NEOWS_NEO_FEED="${MONITOR_RUN_MAX_AGE_HOURS_NEOWS_NEO_FEED:-24}"
MONITOR_RUN_MAX_AGE_HOURS_NEOWS_NEO_BROWSE="${MONITOR_RUN_MAX_AGE_HOURS_NEOWS_NEO_BROWSE:-336}"
MONITOR_RUN_MAX_AGE_HOURS_NEOWS_NEO_LOOKUP="${MONITOR_RUN_MAX_AGE_HOURS_NEOWS_NEO_LOOKUP:-720}"
MONITOR_RUN_MAX_AGE_HOURS_EXOPLANET_PSCOMPPARS="${MONITOR_RUN_MAX_AGE_HOURS_EXOPLANET_PSCOMPPARS:-168}"
MONITOR_RUN_MAX_AGE_HOURS_EXOPLANET_PS="${MONITOR_RUN_MAX_AGE_HOURS_EXOPLANET_PS:-720}"
MONITOR_RUN_MAX_AGE_HOURS_OSDR_DATASETS="${MONITOR_RUN_MAX_AGE_HOURS_OSDR_DATASETS:-168}"
MONITOR_RUN_MAX_AGE_HOURS_OSDR_FILES="${MONITOR_RUN_MAX_AGE_HOURS_OSDR_FILES:-168}"
MONITOR_RUN_MAX_AGE_HOURS_OSDR_ASSAYS="${MONITOR_RUN_MAX_AGE_HOURS_OSDR_ASSAYS:-336}"
MONITOR_RUN_MAX_AGE_HOURS_OSDR_SAMPLES="${MONITOR_RUN_MAX_AGE_HOURS_OSDR_SAMPLES:-336}"
MONITOR_ALERT_WEBHOOK_URL="${MONITOR_ALERT_WEBHOOK_URL:-}"
BACKUP_ROOT="${BACKUP_ROOT:-${ROOT_DIR}/backups/postgres}"
MONITOR_STATUS_FILE="${MONITOR_STATUS_FILE:-${BACKUP_ROOT}/latest_monitor_status.json}"

declare -a ISSUES=()
declare -a PLATFORM_ISSUES=()
declare -a PUBLIC_ISSUES=()
declare -a BACKUP_ISSUES=()
declare -a INGESTION_ISSUES=()
declare -a CERTIFICATE_ISSUES=()

add_issue() {
  local category="$1"
  local message="$2"
  ISSUES+=("${category}|${message}")

  case "${category}" in
    platform)
      PLATFORM_ISSUES+=("${message}")
      ;;
    public)
      PUBLIC_ISSUES+=("${message}")
      ;;
    backup)
      BACKUP_ISSUES+=("${message}")
      ;;
    ingestion)
      INGESTION_ISSUES+=("${message}")
      ;;
    certificate)
      CERTIFICATE_ISSUES+=("${message}")
      ;;
  esac

  echo "ISSUE [${category}]: ${message}" >&2
}

check_container() {
  local container="$1"
  local state
  state="$(/usr/bin/docker inspect --format '{{.State.Status}}' "${container}" 2>/dev/null || true)"
  if [[ "${state}" != "running" ]]; then
    add_issue "platform" "Container ${container} is not running (state=${state:-missing})."
  fi
}

check_ready_endpoint() {
  local category="$1"
  local label="$2"
  local url="$3"
  local body
  body="$(curl --silent --show-error --fail --max-time "${MONITOR_TIMEOUT_SECONDS}" "${url}" 2>/dev/null || true)"
  if [[ -z "${body}" ]]; then
    add_issue "${category}" "${label} readiness endpoint did not return a healthy response from ${url}."
    return
  fi

  BODY="${body}" LABEL="${label}" python3 - <<'PY'
import json
import os
import sys

label = os.environ["LABEL"]
body = os.environ["BODY"]
try:
    payload = json.loads(body)
except json.JSONDecodeError:
    print(f"{label} returned non-JSON content: {body}", file=sys.stderr)
    sys.exit(2)

if payload.get("status") not in {"ok", "degraded"}:
    print(f"{label} returned unexpected status payload: {payload}", file=sys.stderr)
    sys.exit(3)
if payload.get("database") != "ok":
    print(f"{label} database status is not ok: {payload}", file=sys.stderr)
    sys.exit(4)
PY
  local status=$?
  if [[ ${status} -ne 0 ]]; then
    add_issue "${category}" "${label} readiness payload failed validation for ${url}."
  fi
}

check_backup_freshness() {
  local latest_backup
  latest_backup="$(find "${BACKUP_ROOT}" -type f -name '*.dump' -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -n 1 | cut -d' ' -f2- || true)"
  if [[ -z "${latest_backup}" ]]; then
    add_issue "backup" "No PostgreSQL backup dump found under ${BACKUP_ROOT}."
    return
  fi

  local now latest age_hours
  now="$(date +%s)"
  latest="$(stat -c %Y "${latest_backup}")"
  age_hours="$(( (now - latest) / 3600 ))"
  if (( age_hours > MONITOR_BACKUP_MAX_AGE_HOURS )); then
    add_issue "backup" "Latest PostgreSQL backup is ${age_hours}h old (${latest_backup}), exceeding ${MONITOR_BACKUP_MAX_AGE_HOURS}h."
  fi
}

get_run_max_age_hours() {
  local source_name="$1"
  local source_endpoint="$2"

  case "${source_name}/${source_endpoint}" in
    eonet/categories)
      echo "${MONITOR_RUN_MAX_AGE_HOURS_EONET_CATEGORIES}"
      ;;
    eonet/events)
      echo "${MONITOR_RUN_MAX_AGE_HOURS_EONET_EVENTS}"
      ;;
    eonet/layers)
      echo "${MONITOR_RUN_MAX_AGE_HOURS_EONET_LAYERS}"
      ;;
    eonet/sources)
      echo "${MONITOR_RUN_MAX_AGE_HOURS_EONET_SOURCES}"
      ;;
    neows/neo_feed)
      echo "${MONITOR_RUN_MAX_AGE_HOURS_NEOWS_NEO_FEED}"
      ;;
    neows/neo_browse)
      echo "${MONITOR_RUN_MAX_AGE_HOURS_NEOWS_NEO_BROWSE}"
      ;;
    neows/neo_lookup)
      echo "${MONITOR_RUN_MAX_AGE_HOURS_NEOWS_NEO_LOOKUP}"
      ;;
    exoplanet/pscomppars)
      echo "${MONITOR_RUN_MAX_AGE_HOURS_EXOPLANET_PSCOMPPARS}"
      ;;
    exoplanet/ps)
      echo "${MONITOR_RUN_MAX_AGE_HOURS_EXOPLANET_PS}"
      ;;
    osdr/datasets)
      echo "${MONITOR_RUN_MAX_AGE_HOURS_OSDR_DATASETS}"
      ;;
    osdr/files)
      echo "${MONITOR_RUN_MAX_AGE_HOURS_OSDR_FILES}"
      ;;
    osdr/assays)
      echo "${MONITOR_RUN_MAX_AGE_HOURS_OSDR_ASSAYS}"
      ;;
    osdr/samples)
      echo "${MONITOR_RUN_MAX_AGE_HOURS_OSDR_SAMPLES}"
      ;;
    *)
      echo "${MONITOR_RUN_MAX_AGE_HOURS}"
      ;;
  esac
}

check_run_management_freshness() {
  local rows
  rows="$(
    /usr/bin/docker exec \
      -e "PGPASSWORD=${POSTGRES_PASSWORD}" \
      nasahub-postgres \
      psql \
        -U "${POSTGRES_USER}" \
        -d "${POSTGRES_DB}" \
        -t -A -F '|' \
        -c "
          WITH latest_runs AS (
            SELECT
              source_name,
              source_endpoint,
              status,
              run_started_at,
              run_finished_at,
              records_inserted,
              ROW_NUMBER() OVER (
                PARTITION BY source_name, source_endpoint
                ORDER BY run_started_at DESC NULLS LAST, created_at DESC NULLS LAST
              ) AS rn
            FROM tech.run_management
          )
          SELECT
            source_name,
            source_endpoint,
            status,
            run_started_at,
            COALESCE(run_finished_at::text, ''),
            records_inserted
          FROM latest_runs
          WHERE rn = 1
          ORDER BY source_name, source_endpoint;
        " 2>/dev/null || true
  )"

  if [[ -z "${rows}" ]]; then
    add_issue "ingestion" "No latest-run rows could be read from tech.run_management."
    return
  fi

  local now
  now="$(date +%s)"

  while IFS='|' read -r source_name source_endpoint status run_started_at run_finished_at records_inserted; do
    [[ -z "${source_name}" ]] && continue

    local normalized_status
    normalized_status="$(printf '%s' "${status}" | tr '[:upper:]' '[:lower:]')"
    if [[ "${normalized_status}" != "success" ]]; then
      add_issue "ingestion" "Latest run for ${source_name}/${source_endpoint} is not successful (status=${status})."
    fi

    local started_epoch age_hours max_age_hours
    started_epoch="$(date -d "${run_started_at}" +%s 2>/dev/null || true)"
    if [[ -z "${started_epoch}" ]]; then
      add_issue "ingestion" "Unable to parse run_started_at for ${source_name}/${source_endpoint}: ${run_started_at}."
      continue
    fi

    age_hours="$(( (now - started_epoch) / 3600 ))"
    max_age_hours="$(get_run_max_age_hours "${source_name}" "${source_endpoint}")"
    if (( age_hours > max_age_hours )); then
      add_issue "ingestion" "Latest run for ${source_name}/${source_endpoint} is ${age_hours}h old, exceeding ${max_age_hours}h."
    fi
  done <<< "${rows}"
}

check_certificate_expiry() {
  local host enddate end_epoch now days_left
  host="${NASAHUB_PUBLIC_HOST}"

  enddate="$(
    /bin/bash -lc "openssl s_client -connect ${host}:443 -servername ${host} </dev/null 2>/dev/null | openssl x509 -noout -enddate 2>/dev/null" \
      | cut -d= -f2- || true
  )"

  if [[ -z "${enddate}" ]]; then
    add_issue "certificate" "Unable to inspect TLS certificate expiry for ${host}:443."
    return
  fi

  end_epoch="$(date -d "${enddate}" +%s 2>/dev/null || true)"
  if [[ -z "${end_epoch}" ]]; then
    add_issue "certificate" "Unable to parse TLS certificate expiry date for ${host}: ${enddate}."
    return
  fi

  now="$(date +%s)"
  days_left="$(( (end_epoch - now) / 86400 ))"
  if (( days_left < MONITOR_CERT_MIN_DAYS )); then
    add_issue "certificate" "TLS certificate for ${host} expires in ${days_left} day(s), below the ${MONITOR_CERT_MIN_DAYS}-day threshold."
  fi
}

print_issue_section() {
  local label="$1"
  shift
  local -a items=("$@")

  if [[ ${#items[@]} -eq 0 ]]; then
    return
  fi

  echo "${label}:" >&2
  for item in "${items[@]}"; do
    echo "- ${item}" >&2
  done
}

write_monitor_status_file() {
  mkdir -p "$(dirname "${MONITOR_STATUS_FILE}")"

  local overall_status="ok"
  if [[ ${#ISSUES[@]} -gt 0 ]]; then
    overall_status="degraded"
  fi

  local tmp_file="${MONITOR_STATUS_FILE}.tmp"
  PLATFORM_ISSUES_TEXT="$(printf '%s\n' "${PLATFORM_ISSUES[@]}")" \
  PUBLIC_ISSUES_TEXT="$(printf '%s\n' "${PUBLIC_ISSUES[@]}")" \
  BACKUP_ISSUES_TEXT="$(printf '%s\n' "${BACKUP_ISSUES[@]}")" \
  INGESTION_ISSUES_TEXT="$(printf '%s\n' "${INGESTION_ISSUES[@]}")" \
  CERTIFICATE_ISSUES_TEXT="$(printf '%s\n' "${CERTIFICATE_ISSUES[@]}")" \
  OVERALL_STATUS="${overall_status}" \
  ISSUE_COUNT="${#ISSUES[@]}" \
  python3 - <<'PY' > "${tmp_file}"
import json
import os
from datetime import datetime, timezone

def lines(name):
    return [line.strip() for line in os.environ.get(name, "").splitlines() if line.strip()]

categories = {
    "platform": lines("PLATFORM_ISSUES_TEXT"),
    "public": lines("PUBLIC_ISSUES_TEXT"),
    "backup": lines("BACKUP_ISSUES_TEXT"),
    "ingestion": lines("INGESTION_ISSUES_TEXT"),
    "certificate": lines("CERTIFICATE_ISSUES_TEXT"),
}

payload = {
    "checked_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    "overall_status": os.environ["OVERALL_STATUS"],
    "issue_count": int(os.environ["ISSUE_COUNT"]),
    "source": "check_nasahub_health.sh",
    "categories": {
        name: {"issue_count": len(messages), "issues": messages}
        for name, messages in categories.items()
    },
}

print(json.dumps(payload, indent=2))
PY

  mv "${tmp_file}" "${MONITOR_STATUS_FILE}"
}

send_alert_if_configured() {
  if [[ ${#ISSUES[@]} -eq 0 ]]; then
    return
  fi

  if [[ -z "${MONITOR_ALERT_WEBHOOK_URL}" ]]; then
    return
  fi

  local payload
  payload="$(
    PLATFORM_ISSUES_TEXT="$(printf '%s\n' "${PLATFORM_ISSUES[@]}")" \
    PUBLIC_ISSUES_TEXT="$(printf '%s\n' "${PUBLIC_ISSUES[@]}")" \
    BACKUP_ISSUES_TEXT="$(printf '%s\n' "${BACKUP_ISSUES[@]}")" \
    INGESTION_ISSUES_TEXT="$(printf '%s\n' "${INGESTION_ISSUES[@]}")" \
    CERTIFICATE_ISSUES_TEXT="$(printf '%s\n' "${CERTIFICATE_ISSUES[@]}")" \
    python3 - <<'PY'
import json
import os

def lines(name):
    return [line.strip() for line in os.environ.get(name, "").splitlines() if line.strip()]

categories = {
    "platform": lines("PLATFORM_ISSUES_TEXT"),
    "public": lines("PUBLIC_ISSUES_TEXT"),
    "backup": lines("BACKUP_ISSUES_TEXT"),
    "ingestion": lines("INGESTION_ISSUES_TEXT"),
    "certificate": lines("CERTIFICATE_ISSUES_TEXT"),
}

issues = []
for category, messages in categories.items():
    for message in messages:
        issues.append({"category": category, "message": message})

print(json.dumps({
    "text": "NASAHub monitor alert",
    "issue_count": len(issues),
    "categories": categories,
    "issues": issues,
}))
PY
  )"

  curl --silent --show-error --fail \
    --max-time "${MONITOR_TIMEOUT_SECONDS}" \
    -H "Content-Type: application/json" \
    -d "${payload}" \
    "${MONITOR_ALERT_WEBHOOK_URL}" >/dev/null || true
}

check_container "nasahub-postgres"
check_container "nasahub-api"
check_container "nasahub-caddy"
check_ready_endpoint "platform" "Local" "${MONITOR_LOCAL_READY_URL}"
check_ready_endpoint "public" "Public" "${MONITOR_PUBLIC_READY_URL}"
check_backup_freshness
check_run_management_freshness
check_certificate_expiry
write_monitor_status_file
send_alert_if_configured

if [[ ${#ISSUES[@]} -gt 0 ]]; then
  print_issue_section "Platform health issues" "${PLATFORM_ISSUES[@]}"
  print_issue_section "Public availability issues" "${PUBLIC_ISSUES[@]}"
  print_issue_section "Backup issues" "${BACKUP_ISSUES[@]}"
  print_issue_section "Ingestion freshness issues" "${INGESTION_ISSUES[@]}"
  print_issue_section "Certificate issues" "${CERTIFICATE_ISSUES[@]}"
  echo "NASAHub monitoring check failed with ${#ISSUES[@]} issue(s)." >&2
  exit 1
fi

echo "NASAHub monitoring check passed. Categories checked: platform, public, backup, ingestion, certificate."

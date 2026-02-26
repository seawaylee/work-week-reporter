#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="/Users/NikoBelic/app/git/week-reporter"
JOB_SCRIPT="$ROOT_DIR/scripts/weekly_report_job.sh"
LOG_DIR="$ROOT_DIR/logs"
CRON_LOG="$LOG_DIR/weekly_report_cron.log"
CRON_EXPR="30 9 * * 5"
CRON_LINE="$CRON_EXPR $JOB_SCRIPT >> $CRON_LOG 2>&1"

mkdir -p "$LOG_DIR"

existing_cron="$(crontab -l 2>/dev/null || true)"
filtered_cron="$(printf '%s\n' "$existing_cron" | awk -v marker="$JOB_SCRIPT" '$0 !~ marker { print }')"

{
  printf '%s\n' "$filtered_cron"
  printf '%s\n' "$CRON_LINE"
} | awk 'NF || prev { print } { prev = NF }' | crontab -

echo "Installed cron entry:"
crontab -l | grep -F "$JOB_SCRIPT"

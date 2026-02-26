#!/usr/bin/env bash

# Run weekly report generation and always attempt OpenClaw notification.

set -u

ROOT_DIR="/Users/NikoBelic/app/git/week-reporter"
REPORT_SCRIPT="$ROOT_DIR/generate_weekly_report.py"
PYTHON_BIN="${PYTHON_BIN:-/usr/bin/python3}"
OPENCLAW_BIN="${OPENCLAW_BIN:-/Users/NikoBelic/.local/bin/openclaw}"

TARGET_AGENT="sohu"
TARGET_DROP_DIR="$HOME/.openclaw/workspace-sohu/inbox/week-reporter"

LOG_DIR="$ROOT_DIR/logs"
RUN_ID="$(date '+%Y%m%d_%H%M%S')"
RUN_LOG="$LOG_DIR/weekly_report_${RUN_ID}.log"

mkdir -p "$LOG_DIR"

timestamp() {
  date '+%Y-%m-%d %H:%M:%S'
}

log() {
  printf '[%s] %s\n' "$(timestamp)" "$*" | tee -a "$RUN_LOG"
}

find_report_file() {
  local today_file="$ROOT_DIR/周报$(date '+%Y-%m-%d').xlsx"
  if [[ -f "$today_file" ]]; then
    printf '%s\n' "$today_file"
    return 0
  fi
  ls -1t "$ROOT_DIR"/周报*.xlsx 2>/dev/null | head -n 1
}

copy_for_agent() {
  local source_file="$1"
  local dest_dir="$2"
  mkdir -p "$dest_dir"
  local dest_file="$dest_dir/$(basename "$source_file")"
  cp -f "$source_file" "$dest_file"
  printf '%s\n' "$dest_file"
}

build_message() {
  local status="$1"
  local report_file="$2"
  local delivered_file="$3"
  cat <<EOF
【week-reporter定时任务通知】
状态: ${status}
时间: $(timestamp)
主机: $(hostname)
项目目录: ${ROOT_DIR}
执行日志: ${RUN_LOG}
生成Excel: ${report_file:-未生成}
发送给agent的Excel: ${delivered_file:-未提供}
EOF
}

notify_agent() {
  local label="$1"
  shift
  log "Notifying OpenClaw (${label}) ..."
  "$OPENCLAW_BIN" "$@" >>"$RUN_LOG" 2>&1
  return $?
}

job_status="SUCCESS"
report_rc=0
final_rc=0
report_file=""
delivered_file=""

log "===== Weekly report job started ====="

if [[ "${DRY_RUN:-0}" == "1" ]]; then
  job_status="DRY_RUN"
  log "DRY_RUN=1, skip report generation."
else
  if [[ ! -f "$REPORT_SCRIPT" ]]; then
    report_rc=127
    job_status="FAILED:script_not_found"
    log "Report script not found: $REPORT_SCRIPT"
  else
    log "Running report script: $REPORT_SCRIPT"
    (
      cd "$ROOT_DIR" || exit 1
      "$PYTHON_BIN" "$REPORT_SCRIPT"
    ) >>"$RUN_LOG" 2>&1 || report_rc=$?

    if [[ "$report_rc" -ne 0 ]]; then
      job_status="FAILED:report_exit_${report_rc}"
      log "Report script failed with exit code: $report_rc"
    else
      log "Report script finished with exit code 0."
    fi
  fi

  report_file="$(find_report_file || true)"
  if [[ -n "$report_file" && -f "$report_file" ]]; then
    log "Found report file: $report_file"
    delivered_file="$(copy_for_agent "$report_file" "$TARGET_DROP_DIR" 2>>"$RUN_LOG" || true)"
    if [[ -n "$delivered_file" ]]; then
      log "Copied report to agent workspace: $delivered_file"
    else
      log "Failed to copy report to agent workspace."
    fi
  else
    log "No report file found."
    if [[ "$job_status" == "SUCCESS" ]]; then
      job_status="FAILED:no_report_file"
    fi
  fi
fi

notify_ok=1
primary_message="$(build_message "$job_status" "$report_file" "$delivered_file")"
if notify_agent "agent=${TARGET_AGENT}" agent --local --agent "$TARGET_AGENT" --message "$primary_message" --timeout 300 --json; then
  notify_ok=0
  log "OpenClaw notification succeeded via agent=${TARGET_AGENT}."
else
  log "OpenClaw notification failed via agent=${TARGET_AGENT}."
fi

if [[ "$report_rc" -ne 0 ]]; then
  final_rc="$report_rc"
elif [[ "$job_status" == "FAILED:no_report_file" ]]; then
  final_rc=3
fi

if [[ "$notify_ok" -ne 0 && "$final_rc" -eq 0 ]]; then
  final_rc=4
fi

log "===== Weekly report job finished (status=${job_status}, exit=${final_rc}) ====="
exit "$final_rc"

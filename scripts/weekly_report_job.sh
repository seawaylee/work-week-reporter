#!/usr/bin/env bash

# Run weekly report generation and always attempt OpenClaw notification.

set -u

ROOT_DIR="/Users/NikoBelic/app/git/week-reporter"
REPORT_SCRIPT="$ROOT_DIR/generate_weekly_report.py"
PYTHON_BIN="${PYTHON_BIN:-/usr/bin/python3}"
OPENCLAW_BIN="${OPENCLAW_BIN:-/Users/NikoBelic/.local/bin/openclaw}"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env.local}"

TARGET_AGENT="sohu"
TARGET_DROP_DIR="$HOME/.openclaw/workspace-sohu/inbox/week-reporter"
DELIVER_CHANNEL="${DELIVER_CHANNEL:-feishu}"
DELIVER_ACCOUNT="${DELIVER_ACCOUNT:-sohu}"
DELIVER_TO="${DELIVER_TO:-ou_3e6c1be3a3b866454c3d79694956613d}"
TASK_NAME="Odin周报自动生成与投递"

LOG_DIR="$ROOT_DIR/logs"
RUN_ID="$(date '+%Y%m%d_%H%M%S')"
RUN_LOG="$LOG_DIR/weekly_report_${RUN_ID}.log"
RUN_START_AT="$(date '+%Y-%m-%d %H:%M:%S')"

mkdir -p "$LOG_DIR"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  . "$ENV_FILE"
  set +a
fi

timestamp() {
  date '+%Y-%m-%d %H:%M:%S'
}

log() {
  printf '[%s] %s\n' "$(timestamp)" "$*" | tee -a "$RUN_LOG"
}

find_today_report_file() {
  local today_file="$ROOT_DIR/周报$(date '+%Y-%m-%d').xlsx"
  if [[ -f "$today_file" ]]; then
    printf '%s\n' "$today_file"
    return 0
  fi
  return 1
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
  local report_step="$4"
  local copy_step="$5"
  cat <<EOF
【${TASK_NAME}执行报告】
执行ID: ${RUN_ID}
开始时间: ${RUN_START_AT}
当前时间: $(timestamp)
主机: $(hostname)
执行结果: ${status}

已执行任务:
1) 运行周报脚本: ${report_step}
2) 收集并复制Excel到agent收件区: ${copy_step}
3) 发送本条执行报告到sohu agent

产出物:
- 文件规则: 仅允许投递当天文件（周报$(date '+%Y-%m-%d').xlsx）
- 周报文件: ${report_file:-未生成}
- 投递路径: ${delivered_file:-未提供}
- 执行日志: ${RUN_LOG}
EOF
}

build_agent_prompt() {
  local report="$1"
  cat <<EOF
你是自动化任务播报器。请严格原样输出“执行报告正文”，不要改写、不要总结、不要补充任何说明。

执行报告正文：
${report}
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
report_step_desc="未执行"
copy_step_desc="未执行"

log "===== Weekly report job started ====="

if [[ "${DRY_RUN:-0}" == "1" ]]; then
  job_status="DRY_RUN"
  report_step_desc="DRY_RUN（未执行）"
  log "DRY_RUN=1, skip report generation."
else
  if [[ ! -f "$REPORT_SCRIPT" ]]; then
    report_rc=127
    job_status="FAILED:script_not_found"
    report_step_desc="失败（脚本不存在）"
    log "Report script not found: $REPORT_SCRIPT"
  else
    log "Running report script: $REPORT_SCRIPT"
    (
      cd "$ROOT_DIR" || exit 1
      "$PYTHON_BIN" "$REPORT_SCRIPT"
    ) >>"$RUN_LOG" 2>&1 || report_rc=$?

    if [[ "$report_rc" -ne 0 ]]; then
      job_status="FAILED:report_exit_${report_rc}"
      report_step_desc="失败（exit=${report_rc}）"
      log "Report script failed with exit code: $report_rc"
    else
      report_step_desc="成功"
      log "Report script finished with exit code 0."
    fi
  fi

  report_file="$(find_today_report_file || true)"
  if [[ -n "$report_file" && -f "$report_file" ]]; then
    log "Found report file: $report_file"
    delivered_file="$(copy_for_agent "$report_file" "$TARGET_DROP_DIR" 2>>"$RUN_LOG" || true)"
    if [[ -n "$delivered_file" ]]; then
      copy_step_desc="成功"
      log "Copied report to agent workspace: $delivered_file"
    else
      copy_step_desc="失败（复制失败）"
      log "Failed to copy report to agent workspace."
    fi
  else
    copy_step_desc="失败（未找到当天周报文件）"
    log "No today report file found: 周报$(date '+%Y-%m-%d').xlsx"
    if [[ "$job_status" == "SUCCESS" ]]; then
      job_status="FAILED:no_report_file"
    fi
  fi
fi

notify_ok=1
primary_message="$(build_message "$job_status" "$report_file" "$delivered_file" "$report_step_desc" "$copy_step_desc")"
agent_prompt="$(build_agent_prompt "$primary_message")"

# First try visible delivery to chat channel. If it fails, fall back to local run.
if notify_agent "agent=${TARGET_AGENT} deliver:${DELIVER_CHANNEL}/${DELIVER_TO}" \
  agent --agent "$TARGET_AGENT" --message "$agent_prompt" --deliver \
  --reply-channel "$DELIVER_CHANNEL" --reply-account "$DELIVER_ACCOUNT" --reply-to "$DELIVER_TO" \
  --timeout 300 --json; then
  notify_ok=0
  log "OpenClaw notification delivered via channel."
else
  log "Channel delivery failed. Falling back to local agent run."
  if notify_agent "agent=${TARGET_AGENT} local-fallback" \
    agent --local --agent "$TARGET_AGENT" --message "$agent_prompt" --timeout 300 --json; then
    notify_ok=0
    log "OpenClaw notification succeeded via local fallback."
  else
    log "OpenClaw notification failed via both delivery and local fallback."
  fi
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

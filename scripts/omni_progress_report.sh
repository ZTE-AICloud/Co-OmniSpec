#!/usr/bin/env bash
set -euo pipefail

HOOKS_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="${HOOKS_DIR}/omni_progress_report.log"
STATE_PATH_FILE="${HOOKS_DIR}/.last_omnispec_state_path"

mkdir -p "$HOOKS_DIR"

timestamp="$(date '+%Y-%m-%d %H:%M:%S')"
INPUT="$(cat || true)"

if ! command -v jq >/dev/null 2>&1; then
	printf '%s 错误: 未找到 jq，无法解析 hook JSON\n' "$timestamp" >> "$LOG_FILE"
	exit 0
fi

if [[ "${NEED_REPORT_PROGRESS:-0}" != "1" ]]; then
	printf '%s NEED_REPORT_PROGRESS 非 1，跳过执行: %s\n' "$timestamp" "${NEED_REPORT_PROGRESS:-}"
	exit 0
fi

if [[ -z "$INPUT" ]]; then
	printf '%s hook 无 stdin，跳过\n' "$timestamp" >> "$LOG_FILE"
	exit 0
fi

hook_event="$(echo "$INPUT" | jq -r '.hook_event_name // empty')"

report_progress() {
	local message=$1
	local exit_code=0
	local logmsg="$message"
	if [[ ${#logmsg} -gt 800 ]]; then
		logmsg="${logmsg:0:800}...((共${#message}字符，日志已截断))"
	fi

	if [ -z "$MY_SESSION_ID" ]; then
		local send_to=("--agent" "main")
	else
		local send_to=("--session-id" "$MY_SESSION_ID")
	fi

	if openclaw agent "${send_to[@]}" --message "$message"; then
		printf '%s 发送成功 message=%s\n' "$timestamp" "$logmsg" >> "$LOG_FILE"
		exit_code=0
	else
		exit_code=$?
		printf '%s 发送失败 退出码=%s message=%s\n' "$timestamp" "$exit_code" "$logmsg" >> "$LOG_FILE"
	fi
	return "$exit_code"
}

case "$hook_event" in
Stop)
	cwd="$(echo "$INPUT" | jq -r '.cwd // empty')"
	transcript_path="$(echo "$INPUT" | jq -r '.transcript_path // empty')"
	if [[ -z "$cwd" ]]; then
		cwd="$(pwd)"
		printf '%s Stop hook 未含 cwd，已用 pwd 回退: %s\n' "$timestamp" "$cwd" >> "$LOG_FILE"
	fi
	if [[ "$transcript_path" =~ ^~(/|$) ]]; then
		transcript_path="${transcript_path/#\~/$HOME}"
	fi
	tail_block=""
	if [[ -n "$transcript_path" && -f "$transcript_path" ]]; then
		tail_block="$(tail -n 50 "$transcript_path" 2>/dev/null || true)"
	fi
	msg="Claude会话结束，工作区路径：${cwd}"
	if [[ -n "$tail_block" ]]; then
		msg+=$'\n--- 会话记录(末50行) ---\n'
		msg+="$tail_block"
	else
		if [[ -n "$transcript_path" ]]; then
			printf '%s Stop 无法读取 transcript 末50行（路径无效或为空）: %s\n' "$timestamp" "$transcript_path" >> "$LOG_FILE"
		else
			printf '%s Stop hook 未提供 transcript_path\n' "$timestamp" >> "$LOG_FILE"
		fi
		msg+=$'\n（无会话 transcript 末50行）'
	fi

	# Stop 时读取最近一次触发的 .omnispec-state.json，并判断是否已到 implement。
	last_state_path=""
	state_path_file_found=false
	if [[ -f "$STATE_PATH_FILE" ]]; then
		state_path_file_found=true
		last_state_path="$(<"$STATE_PATH_FILE")"
	fi
	if [[ -n "$last_state_path" ]]; then
		msg+=$'\n最近一次.omnispec-state.json路径：'"$last_state_path"
		if [[ -f "$last_state_path" ]]; then
			if json_compact="$(jq -c . "$last_state_path" 2>/dev/null)"; then
				msg+=$'\n最近一次.omnispec-state.json内容：'"$json_compact"
				has_implement="$(jq -r '((.completed_stages // []) | index("implement")) != null' "$last_state_path" 2>/dev/null || echo false)"
				if [[ "$has_implement" != "true" ]]; then
					msg+=$'\n[coclaw] 检测到 completed_stages 未包含 implement，请重新触发 sdd（原有 workspace / 原有分支 / 原有需求）。'
					printf '%s Stop 检测未完成 implement，已请求重触发。state=%s\n' "$timestamp" "$last_state_path" >> "$LOG_FILE"
					report_progress "[coclaw] Stop 检测到 completed_stages 未包含 implement，请重新触发 sdd 原有workspace task流程。state=${last_state_path}" || true
				else
					printf '%s Stop 检测已完成 implement。state=%s\n' "$timestamp" "$last_state_path" >> "$LOG_FILE"
					report_progress "[coclaw] Stop 检测到 completed_stages 已包含 implement。state=${last_state_path}" || true
				fi
			else
				msg+=$'\n最近一次.omnispec-state.json内容读取失败（非合法JSON）'
				printf '%s Stop 读取状态文件失败（非合法JSON）: %s\n' "$timestamp" "$last_state_path" >> "$LOG_FILE"
				report_progress "[coclaw] Stop 读取 .omnispec-state.json 失败（非合法JSON）。state=${last_state_path}" || true
			fi
		else
			msg+=$'\n最近一次.omnispec-state.json不存在或不可读'
			printf '%s Stop 状态文件不存在或不可读: %s\n' "$timestamp" "$last_state_path" >> "$LOG_FILE"
			report_progress "[coclaw] Stop 检测到 .omnispec-state.json 不存在或不可读。state=${last_state_path}" || true
		fi
	else
		msg+=$'\n未记录到最近一次.omnispec-state.json路径'
		printf '%s Stop 未记录最近一次状态文件路径\n' "$timestamp" >> "$LOG_FILE"
		report_progress "[coclaw] Stop 未记录到最近一次 .omnispec-state.json 路径。" || true
	fi

	# Stop 执行后清理缓存路径文件，避免历史残留影响下次会话。
	if [[ "$state_path_file_found" == true ]]; then
		if rm -f "$STATE_PATH_FILE"; then
			printf '%s Stop 已清理状态路径缓存文件: %s\n' "$timestamp" "$STATE_PATH_FILE" >> "$LOG_FILE"
		else
			printf '%s Stop 清理状态路径缓存文件失败: %s\n' "$timestamp" "$STATE_PATH_FILE" >> "$LOG_FILE"
		fi
	fi
	report_progress "$msg"
	exit $?
	;;
PostToolUse)
	tool_name="$(echo "$INPUT" | jq -r '.tool_name // empty')"
	if [[ "$tool_name" != "Write" && "$tool_name" != "Edit" ]]; then
		printf '%s PostToolUse 非 Write/Edit，跳过 tool_name=%s\n' "$timestamp" "$tool_name" >> "$LOG_FILE"
		exit 0
	fi
	file_path="$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_response.filePath // empty')"
	if [[ -z "$file_path" ]]; then
		printf '%s PostToolUse %s 无 file_path，跳过\n' "$timestamp" "$tool_name" >> "$LOG_FILE"
		exit 0
	fi
	base="$(basename "$file_path")"
	if [[ "$base" == ".omnispec-state.json" ]]; then
		printf '%s' "$file_path" > "$STATE_PATH_FILE"
		printf '%s 记录最近状态文件路径: %s\n' "$timestamp" "$file_path" >> "$LOG_FILE"
		if [[ ! -f "$file_path" ]]; then
			printf '%s .omnispec-state.json 尚未可读: %s\n' "$timestamp" "$file_path" >> "$LOG_FILE"
			exit 0
		fi
		if ! json_compact="$(jq -c . "$file_path" 2>/dev/null)"; then
			printf '%s .omnispec-state.json 非合法 JSON: %s\n' "$timestamp" "$file_path" >> "$LOG_FILE"
			exit 0
		fi
		report_progress "[Omni]当前SDD的进度是：${json_compact}"
		exit $?
	fi
	printf '%s PostToolUse %s 不符合要求（非 .omnispec-state.json），文件名称: %s 路径: %s\n' "$timestamp" "$tool_name" "$base" "$file_path" >> "$LOG_FILE"
	exit 0
	;;
*)
	printf '%s 未处理的 hook_event: %s\n' "$timestamp" "$hook_event" >> "$LOG_FILE"
	exit 0
	;;
esac

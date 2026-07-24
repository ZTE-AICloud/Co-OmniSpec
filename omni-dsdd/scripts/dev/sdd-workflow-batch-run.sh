#!/usr/bin/env bash
# SDD 工作流批量回归：在隔离副本中重复执行 express / mini 工作流，用于稳定性验证。
#
# 典型用法：
#   bash "${CLAUDE_PLUGIN_ROOT}/scripts/dev/sdd-workflow-batch-run.sh" express -p /path/to/project
#   bash "${CLAUDE_PLUGIN_ROOT}/scripts/dev/sdd-workflow-batch-run.sh" express -n 3
#   bash "${CLAUDE_PLUGIN_ROOT}/scripts/dev/sdd-workflow-batch-run.sh" express --runs 1,3,5-7
#   bash "${CLAUDE_PLUGIN_ROOT}/scripts/dev/sdd-workflow-batch-run.sh" tail_log -w /tmp/sdd-workspace
#
#export "ANTHROPIC_BASE_URL"="https://api.minimaxi.com/anthropic"
#export "ANTHROPIC_AUTH_TOKEN"="..."

# -----------------------------------------------------------------------------
# 可配置常量
# -----------------------------------------------------------------------------
BATCH_COUNT=10
STATE_POLL_INTERVAL_MIN=10

CLAUDE_BIN="claude"
CLAUDE_TIMEOUT="150m"
CLAUDE_ARGS=(
    --dangerously-skip-permissions
    --debug
    --output-format stream-json
    --verbose
    --disallowed-tools
    Workflow
)
# 需求文档：默认指向仓库内 @doc 软链；可通过 --requirement 覆盖为绝对路径。
TEST_DOC="${TEST_DOC:-@doc/TCF-123456-详细服务变更设计.md}"
MINI_IMPLEMENT_PROMPT="/omni-dsdd:mini.implement"

# prompt 在调用时基于最新 TEST_DOC 拼装，避免顶部展开后无法被命令行参数覆盖。
build_express_prompt() {
    echo "/omni-dsdd:sdd ${TEST_DOC} --workflow express"
}
build_mini_design_prompt() {
    echo "/omni-dsdd:mini.design ${TEST_DOC}"
}
CLAUDE_APPEND_SYSTEM_PROMPT='批量回归模式：必须通过 Skill 工具调用 omni-dsdd 插件技能（express 用 omni-dsdd:sdd，mini 用 omni-dsdd:mini.design / mini.implement）。禁止自造 Workflow、禁止猜测 .claude/workflows 或名为 express 的内置工作流。必须产出 changes/ 目录及 spec.md、design.md 等 SDD 产物。'

# -----------------------------------------------------------------------------
# 初始化
# -----------------------------------------------------------------------------
set -uo pipefail

SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../bash/common.sh
source "${SCRIPT_DIR}/../bash/common.sh"

DEFAULT_WORKSPACE="/tmp/sdd-workspace"

PROJECT=""
WORKSPACE_BASE="${SDD_WORKSPACE:-$DEFAULT_WORKSPACE}"
PROJECT_NAME=""
COMMAND=""
RUNS_SPEC=""
RUN_IDS=()
ACTIVE_PID=""
BATCH_SHOULD_EXIT=false
FAIL_ON_INCOMPLETE=false
FAILED_RUNS=()
STATE_POLL_PID=""
CURRENT_RUN_ID=""

# -----------------------------------------------------------------------------
# 工具函数
# -----------------------------------------------------------------------------
die() {
    echo "错误: $*" >&2
    exit 1
}

resolve_path() {
    local path="$1"
    if [[ "$path" != /* ]]; then
        path="$(CDPATH="" cd "$(dirname "$path")" && pwd)/$(basename "$path")"
    fi
    echo "$path"
}

resolve_omni_plugin_root() {
    if [[ -n "${CLAUDE_PLUGIN_ROOT:-}" && -d "${CLAUDE_PLUGIN_ROOT}" ]]; then
        (CDPATH="" cd "${CLAUDE_PLUGIN_ROOT}" && pwd)
        return
    fi
    (CDPATH="" cd "${SCRIPT_DIR}/../.." && pwd)
}

format_json_file() {
    local file=$1
    local indent=$2

    if command -v jq >/dev/null 2>&1; then
        jq . "$file" | sed "s/^/${indent}/"
    elif command -v python3 >/dev/null 2>&1; then
        python3 -m json.tool "$file" | sed "s/^/${indent}/"
    else
        sed "s/^/${indent}/" "$file"
    fi
}

# 打印目标路径所在分区空间；可选展示工作区目录占用
print_disk_usage() {
    local label="${1:-磁盘}"
    local target="${2:-$WORKSPACE_BASE}"
    local indent="${3:-  }"
    local fs size used avail pct mount workspace_size

    if ! command -v df >/dev/null 2>&1; then
        echo "${indent}${label}: df 不可用"
        return 0
    fi

    read -r fs size used avail pct mount < <(
        df -hP "$target" 2>/dev/null | awk 'NR==2 {print $1, $2, $3, $4, $5, $6}'
    )
    if [[ -z "${fs:-}" ]]; then
        echo "${indent}${label}: 无法读取 $target 所在分区"
        return 0
    fi

    echo "${indent}${label}: ${mount} (${fs})  总 ${size}  已用 ${used}  可用 ${avail} (${pct})"
    if [[ -d "$WORKSPACE_BASE" ]]; then
        workspace_size=$(du -sh "$WORKSPACE_BASE" 2>/dev/null | cut -f1)
        [[ -n "$workspace_size" ]] && echo "${indent}  工作区占用: ${workspace_size}  ($WORKSPACE_BASE)"
    fi

    # 可用空间低于 5GiB 时提示（df -Pk，单位 1K 块）
    local avail_kb=""
    avail_kb=$(df -Pk "$target" 2>/dev/null | awk 'NR==2 {print $4}')
    if [[ -n "$avail_kb" && "$avail_kb" =~ ^[0-9]+$ && "$avail_kb" -lt $((5 * 1024 * 1024)) ]]; then
        echo "${indent}  ⚠️  分区可用空间不足 5G，批量副本可能失败" >&2
    fi
}

# -----------------------------------------------------------------------------
# 路径解析（工作区 / 副本 / 日志）
# -----------------------------------------------------------------------------
workflow_dir_for() {
    echo "$WORKSPACE_BASE/$1"
}

run_dir_for() {
    echo "$(workflow_dir_for "$1")/${PROJECT_NAME}-${2}"
}

run_log_for() {
    echo "$(workflow_dir_for "$1")/${2}_run.log"
}

check_project_dir() {
    [[ -d "$PROJECT" ]] || die "项目目录不存在: $PROJECT"
}

setup_run_env() {
    local run_dir=$1
    export CLAUDE_PLUGIN_ROOT="$(resolve_omni_plugin_root)"
    export CLAUDE_WORKING_DIR="$run_dir"
}

cleanup_run_artifacts() {
    local workflow_dir=$1
    local run_id=$2
    local run_log="$workflow_dir/${run_id}_run.log"
    local stale_dir

    for stale_dir in "$workflow_dir"/*-"${run_id}"; do
        [[ -e "$stale_dir" ]] || continue
        echo "  清理已存在的工作副本: $stale_dir"
        rm -rf "$stale_dir"
    done

    if [[ -f "$run_log" ]]; then
        echo "  清理已存在的日志: $run_log"
        rm -f "$run_log"
    fi
}

prepare_run_workspace() {
    local workflow_dir=$1
    local run_id=$2
    local run_dir="$workflow_dir/${PROJECT_NAME}-${run_id}"

    mkdir -p "$workflow_dir"
    check_project_dir

    cleanup_run_artifacts "$workflow_dir" "$run_id"

    cp -r "$PROJECT" "$run_dir"
}

# -----------------------------------------------------------------------------
# omnispec-state 采集与打印
# -----------------------------------------------------------------------------
find_omnispec_state_files() {
    find "$1/changes" -mindepth 3 -maxdepth 3 -path '*/.runs/.omnispec-state.json' 2>/dev/null | sort
}

print_omnispec_state_body() {
    local run_dir=$1
    local indent="${2:-  }"
    local state_file
    local -a state_files=()

    while IFS= read -r state_file; do
        [[ -n "$state_file" ]] && state_files+=("$state_file")
    done < <(find_omnispec_state_files "$run_dir")

    if ((${#state_files[@]} == 0)); then
        echo "${indent}未找到: ${run_dir}/changes/*/.runs/.omnispec-state.json"
        return 1
    fi

    for state_file in "${state_files[@]}"; do
        echo "${indent}路径: $state_file"
        format_json_file "$state_file" "$indent"
        echo ""
    done
}

print_state_banner() {
    local title=$1
    local run_dir=$2
    local indent="${3:-  }"

    echo ""
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] --- ${title} ---"
    print_omnispec_state_body "$run_dir" "$indent" || true
    echo "${indent}---"
    echo ""
}

# -----------------------------------------------------------------------------
# session_id 采集
# -----------------------------------------------------------------------------
extract_session_ids_from_run_log() {
    local run_log=$1

    [[ -f "$run_log" ]] || return 0

    if command -v jq >/dev/null 2>&1; then
        jq -r 'select(.type == "system" and .subtype == "init") | .session_id' "$run_log" 2>/dev/null \
            | awk 'NF && !seen[$0]++'
        return 0
    fi

    if command -v python3 >/dev/null 2>&1; then
        python3 - "$run_log" <<'PY'
import json
import sys

seen = set()
with open(sys.argv[1], encoding="utf-8", errors="replace") as fh:
    for line in fh:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("type") == "system" and obj.get("subtype") == "init":
            sid = (obj.get("session_id") or "").strip()
            if sid and sid not in seen:
                seen.add(sid)
                print(sid)
PY
        return 0
    fi

    grep -o '"session_id":"[^"]*"' "$run_log" 2>/dev/null | cut -d'"' -f4 | awk 'NF && !seen[$0]++'
}

# -----------------------------------------------------------------------------
# 周期检测与后置报告
# -----------------------------------------------------------------------------
start_state_poll_watcher() {
    local run_id=$1
    local run_dir=$2
    local interval_sec=$((STATE_POLL_INTERVAL_MIN * 60))

    stop_state_poll_watcher
    [[ "$interval_sec" -gt 0 ]] || return 0
    [[ -n "$run_dir" && -d "$run_dir" ]] || return 0

    (
        while true; do
            sleep "$interval_sec"
            print_state_banner "周期状态 (run ${run_id}, 每 ${STATE_POLL_INTERVAL_MIN} 分钟)" "$run_dir"
            print_disk_usage "周期磁盘" "$WORKSPACE_BASE"
        done
    ) &
    STATE_POLL_PID=$!
}

stop_state_poll_watcher() {
    if [[ -n "${STATE_POLL_PID:-}" ]]; then
        kill "$STATE_POLL_PID" 2>/dev/null || true
        wait "$STATE_POLL_PID" 2>/dev/null || true
        STATE_POLL_PID=""
    fi
}

print_post_run_session_log() {
    local run_id=$1
    local run_log=$2
    local run_dir=$3
    local sid
    local -a session_ids=()

    echo "  --- 会话 ID (run ${run_id}) ---"
    if [[ ! -f "$run_log" ]]; then
        echo "  未找到运行日志: $run_log"
        echo "  ---"
        return 0
    fi

    while IFS= read -r sid; do
        [[ -n "$sid" ]] && session_ids+=("$sid")
    done < <(extract_session_ids_from_run_log "$run_log")

    if ((${#session_ids[@]} == 0)); then
        echo "  未从日志解析到 session_id"
        echo "  日志: $run_log"
        echo "  ---"
        return 0
    fi

    echo "  日志: $run_log"
    if ((${#session_ids[@]} == 1)); then
        echo "  session_id: ${session_ids[0]}"
        echo "  续跑: cd $(printf '%q' "$run_dir") && claude --resume ${session_ids[0]}"
    else
        local idx=1
        for sid in "${session_ids[@]}"; do
            echo "  会话 ${idx}: $sid"
            echo "  续跑 ${idx}: cd $(printf '%q' "$run_dir") && claude --resume $sid"
            ((idx++)) || true
        done
    fi
    echo "  ---"
}

print_post_run_report() {
    local run_id=$1
    local mode=$2
    local run_dir
    local run_log

    run_dir="$(run_dir_for "$mode" "$run_id")"
    run_log="$(run_log_for "$mode" "$run_id")"

    print_post_run_session_log "$run_id" "$run_log" "$run_dir"
    echo "  --- 后置状态 (run ${run_id}) ---"
    print_omnispec_state_body "$run_dir" "  " || true
    echo "  ---"
}

# -----------------------------------------------------------------------------
# 产出校验与批量汇总
# -----------------------------------------------------------------------------
find_feature_artifact() {
    local run_dir=$1
    local artifact_name=$2
    find "$run_dir/changes" -mindepth 2 -maxdepth 2 -name "$artifact_name" 2>/dev/null | head -1
}

validate_run() {
    local mode=$1
    local run_id=$2
    local run_dir artifact_name fail_hint artifact

    run_dir="$(run_dir_for "$mode" "$run_id")"
    case "$mode" in
        express)
            artifact_name="spec.md"
            fail_hint="未找到 changes/*/spec.md（可能未走 omni-dsdd:sdd）"
            ;;
        mini)
            artifact_name="design.md"
            fail_hint="未找到 changes/*/design.md（可能未走 omni-dsdd:mini.design）"
            ;;
        *)
            die "未知工作流模式: $mode"
            ;;
    esac

    artifact="$(find_feature_artifact "$run_dir" "$artifact_name")"
    if [[ -n "$artifact" && -f "$artifact" ]]; then
        echo "  ✅ 产出校验通过: $artifact"
        return 0
    fi

    echo "  ⚠️  产出校验失败: ${fail_hint}" >&2
    FAILED_RUNS+=("$run_id")
    return 1
}

print_batch_summary() {
    local project_q runs_list

    if ((${#FAILED_RUNS[@]} == 0)); then
        echo "=============================================="
        echo "全部轮次产出校验通过"
        return 0
    fi

    project_q=$(printf '%q' "$PROJECT")
    runs_list=$(IFS=,; echo "${FAILED_RUNS[*]}")

    echo "=============================================="
    echo "未完成轮次: ${FAILED_RUNS[*]}"
    echo "补跑示例:"
    echo "  $(printf '%q' "$0") ${COMMAND} -p ${project_q} --runs ${runs_list}"
    echo "检查报告:"
    echo "  bash \"\${CLAUDE_PLUGIN_ROOT}/scripts/dev/sdd-workflow-batch-check-express.sh\" -p ${project_q} -y"
    if [[ "$FAIL_ON_INCOMPLETE" == true ]]; then
        return 1
    fi
    return 0
}

# -----------------------------------------------------------------------------
# Claude 执行
# -----------------------------------------------------------------------------
on_batch_interrupt() {
    BATCH_SHOULD_EXIT=true
    echo "" >&2
    echo "收到 Ctrl+C，正在停止当前运行..." >&2
    stop_state_poll_watcher
    if [[ -n "$ACTIVE_PID" ]]; then
        kill -INT "$ACTIVE_PID" 2>/dev/null || kill -TERM "$ACTIVE_PID" 2>/dev/null || true
    fi
    exit 130
}

run_claude_logged() {
    local run_log=$1
    local prompt=$2
    local log_mode="${3:-}"
    local run_dir="${4:-}"
    local -a cmd

    cmd=(timeout "$CLAUDE_TIMEOUT" "$CLAUDE_BIN" "${CLAUDE_ARGS[@]}")
    if [[ -n "${CLAUDE_APPEND_SYSTEM_PROMPT:-}" ]]; then
        cmd+=(--append-system-prompt "$CLAUDE_APPEND_SYSTEM_PROMPT")
    fi
    cmd+=(-p "$prompt")

    if [[ -n "$run_dir" ]]; then
        start_state_poll_watcher "$CURRENT_RUN_ID" "$run_dir"
    fi

    if [[ "$log_mode" == "--append" ]]; then
        "${cmd[@]}" >>"$run_log" 2>&1 &
    else
        "${cmd[@]}" >"$run_log" 2>&1 &
    fi
    ACTIVE_PID=$!
    wait "$ACTIVE_PID" 2>/dev/null || true
    local exit_code=$?
    ACTIVE_PID=""
    stop_state_poll_watcher
    return "$exit_code"
}

run_workflow_round() {
    local mode=$1
    local run_id=$2
    shift 2

    local workflow_dir run_dir run_log
    workflow_dir="$(workflow_dir_for "$mode")"
    run_dir="$(run_dir_for "$mode" "$run_id")"
    run_log="$(run_log_for "$mode" "$run_id")"

    prepare_run_workspace "$workflow_dir" "$run_id"
    setup_run_env "$run_dir"
    cd "$run_dir" || exit 1
    echo "  CLAUDE_PLUGIN_ROOT=$CLAUDE_PLUGIN_ROOT"
    echo "  CLAUDE_WORKING_DIR=$CLAUDE_WORKING_DIR"
    CURRENT_RUN_ID="$run_id"

    while [[ $# -gt 0 ]]; do
        local log_mode="" prompt
        if [[ "$1" == "--append" ]]; then
            log_mode="--append"
            shift
        fi
        [[ $# -gt 0 ]] || die "run_workflow_round: 缺少 prompt 参数"
        prompt=$1
        shift
        run_claude_logged "$run_log" "$prompt" "$log_mode" "$run_dir"
    done

    cd "$SCRIPT_DIR" || exit 1
}

express_workflow() {
    run_workflow_round express "$1" "$(build_express_prompt)"
}

mini_workflow() {
    run_workflow_round mini "$1" "$(build_mini_design_prompt)" --append "$MINI_IMPLEMENT_PROMPT"
}

run_batch() {
    local mode=$1
    local runner=$2

    command -v "$CLAUDE_BIN" >/dev/null 2>&1 || die "${CLAUDE_BIN} 命令未找到，请先安装"

    trap on_batch_interrupt INT TERM

    echo "项目:     $PROJECT"
    echo "工作区:   $(workflow_dir_for "$mode")"
    echo "运行编号: ${RUN_IDS[*]}"
    if [[ "$STATE_POLL_INTERVAL_MIN" -gt 0 ]]; then
        echo "周期状态: 每 ${STATE_POLL_INTERVAL_MIN} 分钟打印 omnispec-state 与磁盘空间"
    else
        echo "周期状态: 已关闭"
    fi
    print_disk_usage "磁盘（批量开始）" "$WORKSPACE_BASE" ""
    check_project_dir

    local run_id start_time end_time duration minutes
    for run_id in "${RUN_IDS[@]}"; do
        if [[ "$BATCH_SHOULD_EXIT" == true ]]; then
            exit 130
        fi
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始运行 ${mode} ${run_id}"
        start_time=$(date +%s)
        "$runner" "$run_id"
        validate_run "$mode" "$run_id" || true
        print_post_run_report "$run_id" "$mode"
        end_time=$(date +%s)
        duration=$((end_time - start_time))
        minutes=$(awk "BEGIN {printf \"%.2f\", $duration/60}")
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ${mode} ${run_id} 结束, 用时 ${minutes} 分钟"
        print_disk_usage "磁盘（run ${run_id} 结束）" "$WORKSPACE_BASE" "  "
        echo ""
    done

    print_batch_summary || die "存在未完成轮次（已启用 --fail-on-incomplete）"
    trap - INT TERM
}

# -----------------------------------------------------------------------------
# tail_log
# -----------------------------------------------------------------------------
on_tail_log_interrupt() {
    echo "" >&2
    echo "已退出日志监控" >&2
    jobs -p | xargs -r kill -INT 2>/dev/null || true
    exit 130
}

tail_log_find_latest() {
    local newest="" newest_num=0 log num
    for log in "$WORKSPACE_BASE"/*/*_run.log; do
        if [[ -f "$log" ]]; then
            num=$(basename "$log" | sed 's/_run\.log$//')
            if [[ "$num" =~ ^[0-9]+$ ]] && [[ "$num" -gt "$newest_num" ]]; then
                newest="$log"
                newest_num=$num
            fi
        fi
    done
    echo "$newest"
}

tail_log_format_line() {
    local line=$1
    echo "$line" | jq -r '
        if .type == "assistant" and .message.content[0].type == "text" then
            .message.content[0].text
        elif .type == "assistant" and .message.content[0].type == "tool_use" then
            "🔧 " + (.message.content[0].name // "tool") + ": " + (.message.content[0].input | to_entries | map("\(.key)=\(.value | tostring | .[0:500])") | join(" "))
        elif .type == "system" and .subtype == "task_progress" then
            "📝 " + .description + " (" + (.usage.duration_ms / 1000 | tostring) + "s)"
        else
            empty
        end
    ' 2>/dev/null || true
}

tail_log() {
    local current_log current_num monitored_log monitored_num
    local tail_pid checker_pid

    current_log=$(tail_log_find_latest)
    [[ -n "$current_log" ]] || die "未找到运行中的日志文件（工作区: $WORKSPACE_BASE）"

    trap on_tail_log_interrupt INT TERM

    echo "工作区: $WORKSPACE_BASE"
    echo "监控日志: $current_log"
    echo "检测到新日志文件时自动切换，按 Ctrl+C 退出"
    echo "=============================================="

    current_num=$(basename "$current_log" | sed 's/_run\.log$//')

    while true; do
        monitored_log="$current_log"
        monitored_num=$current_num

        coproc TAILPROC { tail -f -n 1 "$monitored_log" 2>/dev/null; }
        tail_pid=$TAILPROC_PID

        (
            while sleep 2; do
                local newest new_num
                newest=$(tail_log_find_latest 2>/dev/null)
                if [[ -n "$newest" ]]; then
                    new_num=$(basename "$newest" | sed 's/_run\.log$//')
                    if [[ "$new_num" -gt "$monitored_num" ]]; then
                        kill -PIPE "$tail_pid" 2>/dev/null || kill -TERM "$tail_pid" 2>/dev/null || true
                        exit 0
                    fi
                fi
            done
        ) &
        checker_pid=$!

        while IFS= read -r line <&"${TAILPROC[0]}"; do
            tail_log_format_line "$line"
        done

        kill "$checker_pid" 2>/dev/null || true
        wait "$checker_pid" 2>/dev/null || true
        kill "$tail_pid" 2>/dev/null || true
        wait "$tail_pid" 2>/dev/null || true

        current_log=$(tail_log_find_latest)
        current_num=$(basename "$current_log" | sed 's/_run\.log$//')
        if [[ -n "$current_log" && "$current_num" -gt "$monitored_num" ]]; then
            echo ""
            echo "=============================================="
            echo "切换到新日志: $current_log"
            echo "=============================================="
            continue
        fi
        break
    done

    trap - INT TERM
}

# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------
usage() {
    cat <<EOF
Usage: sdd-workflow-batch-run.sh <command> [options]

命令:
  express   运行 express 批量（默认 ${BATCH_COUNT} 次，工作区 .../express/）
  mini      运行 mini 批量（默认 ${BATCH_COUNT} 次，工作区 .../mini/）
  tail_log  实时监控最新运行的日志输出

选项:
  -p, --project <path>    被测项目目录（默认: CLAUDE_WORKING_DIR 或当前目录）
  -w, --workspace <path>  工作区根目录（默认: /tmp/sdd-workspace）
  -n, --count <n>         批量次数，运行编号 1..n（与 --runs 互斥）
  --runs <spec>           指定运行编号，如 1,3,5 或 1-5 或 1-3,7,10
  --fail-on-incomplete    任一轮未产出 changes/*/spec.md 时最终以非零退出
  --state-poll-interval <min>
                          运行中每 N 分钟打印一次 omnispec-state（默认 10；0 关闭）
  --requirement <path>    覆盖默认需求文档路径，【必须为绝对路径】（以 / 开头）
                          默认: @doc/TCF-123456-详细服务变更设计.md
  -h, --help              显示帮助

环境变量:
  SDD_PROJECT      同 --project
  SDD_WORKSPACE    同 --workspace
  SDD_BATCH_COUNT  同 --count
  SDD_STATE_POLL_INTERVAL  同 --state-poll-interval（分钟）

说明:
  每次运行前若工作副本或日志已存在，会先删除再重新拷贝项目，保证隔离环境干净。
  每轮自动 export CLAUDE_PLUGIN_ROOT / CLAUDE_WORKING_DIR，并禁止 Workflow 工具以防偏航。
  Claude 运行期间按间隔周期打印 omnispec-state 与磁盘空间（若开启周期检测）。
  每轮结束后打印 session_id、omnispec-state 及磁盘空间。
  结束后校验 changes/*/spec.md；失败轮次可用 --runs 补跑。

示例:
  sdd-workflow-batch-run.sh express
  sdd-workflow-batch-run.sh express -p /path/to/op-aif-wsm -n 5
  sdd-workflow-batch-run.sh express --runs 2,4,6
  sdd-workflow-batch-run.sh mini --project . --workspace /tmp/sdd-workspace --runs 1-3
  sdd-workflow-batch-run.sh tail_log -w /tmp/sdd-workspace
EOF
}

parse_runs_spec() {
    local spec=$1
    local -a ids=()
    local part start end i

    [[ -n "$spec" ]] || die "--runs 需要指定编号，如 1,3,5-7"

    IFS=',' read -ra parts <<< "$spec"
    for part in "${parts[@]}"; do
        part="${part//[[:space:]]/}"
        [[ -n "$part" ]] || continue
        if [[ "$part" =~ ^([0-9]+)-([0-9]+)$ ]]; then
            start="${BASH_REMATCH[1]}"
            end="${BASH_REMATCH[2]}"
            [[ "$start" -le "$end" ]] || die "无效区间: $part（起始编号不能大于结束编号）"
            for ((i = start; i <= end; i++)); do
                ids+=("$i")
            done
        elif [[ "$part" =~ ^[0-9]+$ ]]; then
            ids+=("$part")
        else
            die "无效运行编号: $part（支持格式: 3 或 1-5）"
        fi
    done

    ((${#ids[@]} > 0)) || die "--runs 未解析到有效编号: $spec"
    RUN_IDS=("${ids[@]}")
}

resolve_run_ids() {
    local count=$1

    if [[ -n "$RUNS_SPEC" ]]; then
        parse_runs_spec "$RUNS_SPEC"
        return
    fi

    [[ "$count" =~ ^[0-9]+$ ]] || die "批量次数必须为正整数: $count"
    ((count > 0)) || die "批量次数必须大于 0: $count"

    local -a ids=()
    local i
    for ((i = 1; i <= count; i++)); do
        ids+=("$i")
    done
    RUN_IDS=("${ids[@]}")
}

parse_args() {
    local count_override=""

    if [[ -n "${SDD_BATCH_COUNT:-}" ]]; then
        count_override="$SDD_BATCH_COUNT"
    fi
    if [[ -n "${SDD_STATE_POLL_INTERVAL:-}" ]]; then
        STATE_POLL_INTERVAL_MIN="$SDD_STATE_POLL_INTERVAL"
    fi

    while [[ $# -gt 0 ]]; do
        case "$1" in
            express|mini|tail_log)
                COMMAND="$1"
                shift
                ;;
            -p|--project)
                [[ -n "${2:-}" ]] || die "--project 需要指定路径"
                PROJECT="$2"
                shift 2
                ;;
            -w|--workspace)
                [[ -n "${2:-}" ]] || die "--workspace 需要指定路径"
                WORKSPACE_BASE="$2"
                shift 2
                ;;
            -n|--count)
                [[ -n "${2:-}" ]] || die "--count 需要指定次数"
                count_override="$2"
                shift 2
                ;;
            --runs)
                [[ -n "${2:-}" ]] || die "--runs 需要指定编号"
                RUNS_SPEC="$2"
                shift 2
                ;;
            --fail-on-incomplete)
                FAIL_ON_INCOMPLETE=true
                shift
                ;;
            --state-poll-interval)
                [[ -n "${2:-}" ]] || die "--state-poll-interval 需要指定分钟数"
                STATE_POLL_INTERVAL_MIN="$2"
                shift 2
                ;;
            --requirement)
                [[ -n "${2:-}" ]] || die "--requirement 需要指定需求文档绝对路径（用法: --requirement /abs/path/to/doc.md）"
                if [[ "$2" != /* ]]; then
                    die "--requirement 必须是绝对路径（以 / 开头），当前: $2"
                fi
                TEST_DOC="$2"
                shift 2
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                die "未知参数: $1（使用 --help）"
                ;;
        esac
    done

    if [[ -n "$RUNS_SPEC" && -n "$count_override" ]]; then
        die "--runs 与 --count/-n 不能同时使用"
    fi

    COMMAND="${COMMAND:-express}"

    if [[ -z "$PROJECT" ]]; then
        if [[ -n "${SDD_PROJECT:-}" ]]; then
            PROJECT="$SDD_PROJECT"
        else
            PROJECT="$(get_working_dir)"
        fi
    fi

    PROJECT="$(resolve_path "$PROJECT")"
    WORKSPACE_BASE="$(resolve_path "$WORKSPACE_BASE")"
    PROJECT_NAME="$(basename "$PROJECT")"

    if [[ "$COMMAND" == "express" || "$COMMAND" == "mini" ]]; then
        [[ "$STATE_POLL_INTERVAL_MIN" =~ ^[0-9]+$ ]] \
            || die "state-poll-interval 必须为非负整数: $STATE_POLL_INTERVAL_MIN"
        resolve_run_ids "${count_override:-$BATCH_COUNT}"
    fi
}

# -----------------------------------------------------------------------------
# 入口
# -----------------------------------------------------------------------------
parse_args "$@"

case "$COMMAND" in
    express)
        run_batch express express_workflow
        ;;
    mini)
        run_batch mini mini_workflow
        ;;
    tail_log)
        tail_log
        ;;
    *)
        usage
        exit 1
        ;;
esac

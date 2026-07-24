#!/usr/bin/env bash
# Express 批量回归结果检查：按指定轮次校验产出并生成对比报告。
#
# 典型用法：
#   bash "${CLAUDE_PLUGIN_ROOT}/scripts/dev/sdd-workflow-batch-check-express.sh" -p /path/to/project
#   bash "${CLAUDE_PLUGIN_ROOT}/scripts/dev/sdd-workflow-batch-check-express.sh" -w /tmp/sdd-workspace -n 5 -y
#   bash "${CLAUDE_PLUGIN_ROOT}/scripts/dev/sdd-workflow-batch-check-express.sh" -p /path/to/project --runs 1-3,7 -y

# -----------------------------------------------------------------------------
# 可配置常量
# -----------------------------------------------------------------------------
BATCH_COUNT=10
DEFAULT_WORKSPACE="/tmp/sdd-workspace"
HTML_REPORT_FILE="express-workflow-results.html"
# 详情表除「运行次」列外的列数（用于 colspan）
TABLE_DETAIL_COLS=15

# 特性产出检查项：kind|相对路径|终端展示名
# kind: file | dir | nested（目录+文件）
readonly -a FEATURE_ARTIFACTS=(
    "file|spec.md|spec.md"
    "file|design.md|design.md"
    "file|tasks.md|tasks.md"
    "file|research.md|research.md"
    "file|quickstart.md|quickstart.md"
    "file|data-model.md|data-model.md"
    "nested|checklists/requirements.md|checklists/requirements.md"
    "nested|contracts/api-contract.md|contracts/api-contract.md"
    "dir|.runs|.runs"
    "file|.runs/.omnispec-state.json|.omnispec-state.json"
)

# -----------------------------------------------------------------------------
# 初始化
# -----------------------------------------------------------------------------
set -uo pipefail

SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../bash/common.sh
source "${SCRIPT_DIR}/../bash/common.sh"

PROJECT=""
WORKSPACE_BASE="${SDD_WORKSPACE:-$DEFAULT_WORKSPACE}"
PROJECT_NAME=""
RUNS_SPEC=""
RUN_IDS=()
ASSUME_YES=false

# 单轮检查上下文（load_run_context 填充，供终端/HTML 复用）
CTX_RUN_ID=""
CTX_RUN_DIR=""
CTX_FEAT_DIRS=()
CTX_FEAT_COUNT=0
CTX_CODE_MOD=""
CTX_TEST_NEW=""
CTX_STEPS=""
CTX_RESULT=""

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

mark_ok() { echo "✅"; }
mark_fail() { echo "❌"; }

# -----------------------------------------------------------------------------
# 路径解析（工作区 / 副本）
# -----------------------------------------------------------------------------
# express 专用检查脚本，mode 固定为 "express"
WORKFLOW_MODE="express"

workflow_dir_for() {
    echo "$WORKSPACE_BASE/${WORKFLOW_MODE}"
}

run_dir_for() {
    echo "$(workflow_dir_for)/${PROJECT_NAME}-${1}"
}

# -----------------------------------------------------------------------------
# 特性目录与异常检测
# -----------------------------------------------------------------------------
list_feature_dirs() {
    local run_dir=$1
    local -a names=()
    local entry name

    for entry in "$run_dir"/changes/*/; do
        [[ -d "$entry" ]] || continue
        name="$(basename "$entry")"
        names+=("$name")
    done

    if ((${#names[@]} > 0)); then
        printf '%s\n' "${names[@]}"
    fi
}

is_anomaly_dir() {
    case "$1" in
        feature|master|"123-design-changes") echo "yes" ;;
        *) echo "no" ;;
    esac
}

anomaly_desc_for() {
    case "$1" in
        feature) echo "空目录" ;;
        master) echo "目录名异常（应用特性名，不应用分支名）" ;;
        "123-design-changes") echo "几乎空" ;;
        *) echo "" ;;
    esac
}

feat_dir_for() {
    echo "$1/changes/$2"
}

# -----------------------------------------------------------------------------
# 产出文件检查
# -----------------------------------------------------------------------------
artifact_exists() {
    local feat_dir=$1
    local kind=$2
    local rel=$3

    case "$kind" in
        file)
            [[ -f "$feat_dir/$rel" ]]
            ;;
        dir)
            [[ -d "$feat_dir/$rel" ]]
            ;;
        nested)
            [[ -d "$feat_dir/$(dirname "$rel")" && -f "$feat_dir/$rel" ]]
            ;;
        *)
            return 1
            ;;
    esac
}

feature_artifact_marks() {
    local feat_dir=$1
    local sep=$2
    local def kind rel _label
    local -a marks=()

    for def in "${FEATURE_ARTIFACTS[@]}"; do
        IFS='|' read -r kind rel _label <<< "$def"
        if artifact_exists "$feat_dir" "$kind" "$rel"; then
            marks+=("$(mark_ok)")
        else
            marks+=("$(mark_fail)")
        fi
    done

    local IFS="$sep"
    echo "${marks[*]}"
}

print_feature_artifacts() {
    local feat_dir=$1
    local indent=$2
    local def kind rel label

    for def in "${FEATURE_ARTIFACTS[@]}"; do
        IFS='|' read -r kind rel label <<< "$def"
        if artifact_exists "$feat_dir" "$kind" "$rel"; then
            echo "${indent}✅ ${label}"
        else
            echo "${indent}❌ ${label}"
        fi
    done
}

# -----------------------------------------------------------------------------
# 运行指标（git / metrics）
# -----------------------------------------------------------------------------
read_omnispec_state() {
    local run_dir=$1
    local state_file

    state_file=$(find "$run_dir" -path "*/.runs/.omnispec-state.json" 2>/dev/null | head -1)
    if [[ -n "$state_file" && -f "$state_file" ]]; then
        python3 << PYEOF
import json
state_file = "$state_file"
with open(state_file) as f:
    data = json.load(f)
    stages = data.get("completed_stages", [])
    result = data.get("execute_result", "N/A")
    total = len(stages)
    print(f"{total}步: {'->'.join(stages)}")
    print(f"RESULT:{result}")
PYEOF
    else
        echo "无omnispec-state"
        echo "RESULT:N/A"
    fi
}

read_metrics_raw() {
    local run_dir=$1

    # 优先从 .omnispec-state.json 读取（更完整）
    read_omnispec_state "$run_dir"
}

parse_metrics_raw() {
    local raw=$1
    local -n out_steps=$2
    local -n out_result=$3

    out_steps=$(echo "$raw" | head -1)
    out_result=$(echo "$raw" | grep "^RESULT:" | cut -d: -f2-)
}

read_git_worktree_stats() {
    local dir=$1
    local modified=0 tests=0
    local porcelain

    if ! cd "$dir" 2>/dev/null; then
        echo "0|0"
        return
    fi

    porcelain=$(git status --porcelain 2>/dev/null) || {
        cd - > /dev/null 2>&1
        echo "0|0"
        return
    }

    modified=$(echo "$porcelain" | grep "^ M" | grep -v "/changes/" | wc -l)
    tests=$(echo "$porcelain" | grep -E "^\?\?|^\ M" | grep -v "/changes/" | grep -E "_test\.go$" | wc -l)
    cd - > /dev/null 2>&1
    echo "${modified}|${tests}"
}

format_code_mod() {
    local modified=$1
    if [[ "$modified" -gt 0 ]]; then
        echo "✅(${modified}文件)"
    else
        echo "❌无"
    fi
}

format_test_new() {
    local tests=$1
    if [[ "$tests" -gt 0 ]]; then
        echo "✅有"
    else
        echo "❌无"
    fi
}

# -----------------------------------------------------------------------------
# 单轮上下文与检查输出
# -----------------------------------------------------------------------------
load_run_context() {
    local run_id=$1
    local metrics_raw git_stats modified tests

    CTX_RUN_ID="$run_id"
    CTX_RUN_DIR="$(run_dir_for "$run_id")"
    CTX_FEAT_DIRS=()
    while IFS= read -r name; do
        [[ -n "$name" ]] && CTX_FEAT_DIRS+=("$name")
    done < <(list_feature_dirs "$CTX_RUN_DIR")
    CTX_FEAT_COUNT=${#CTX_FEAT_DIRS[@]}

    metrics_raw=$(read_metrics_raw "$CTX_RUN_DIR")
    parse_metrics_raw "$metrics_raw" CTX_STEPS CTX_RESULT

    IFS='|' read -r modified tests < <(read_git_worktree_stats "$CTX_RUN_DIR")
    CTX_CODE_MOD=$(format_code_mod "$modified")
    CTX_TEST_NEW=$(format_test_new "$tests")
}

print_run_summary_line() {
    echo "  代码: $CTX_CODE_MOD | 用例: $CTX_TEST_NEW"
    echo "  步骤: $CTX_STEPS | 结果: $CTX_RESULT"
}

print_run_check() {
    local run_id=$1
    local feat_name feat_path is_anomaly

    load_run_context "$run_id"

    if [[ ! -d "$CTX_RUN_DIR" ]]; then
        echo "Run ${run_id}: 目录不存在 ($CTX_RUN_DIR)"
        echo ""
        return 1
    fi

    echo "=== Run ${run_id} (特性目录数: ${CTX_FEAT_COUNT}) ==="

    if ((${#CTX_FEAT_DIRS[@]} == 0)); then
        echo "  （无 changes/* 特性目录）"
    fi

    for feat_name in "${CTX_FEAT_DIRS[@]}"; do
        is_anomaly=$(is_anomaly_dir "$feat_name")
        if [[ "$is_anomaly" == "yes" ]]; then
            echo "  [异常] $feat_name"
        else
            echo "  特性: $feat_name"
        fi
        print_feature_artifacts "$(feat_dir_for "$CTX_RUN_DIR" "$feat_name")" "    "
    done

    print_run_summary_line
    echo ""
}

append_missing_run_row() {
    local run_id=$1
    local output_file=$2
    local message=$3

    echo "<tr><td><strong>${run_id}</strong></td><td colspan=\"${TABLE_DETAIL_COLS}\" class=\"anomaly\">${message}</td></tr>" >> "$output_file"
}

append_empty_features_row() {
    local output_file=$1

    echo "<tr><td><strong>${CTX_RUN_ID}</strong></td><td colspan=\"${TABLE_DETAIL_COLS}\">（无特性目录） 代码: ${CTX_CODE_MOD} | 用例: ${CTX_TEST_NEW} | 步骤: ${CTX_STEPS} | 结果: ${CTX_RESULT}</td></tr>" >> "$output_file"
}

append_feature_html_row() {
    local output_file=$1
    local row=$2
    local feat_name=$3
    local feat_path=$4
    local is_anomaly=$5
    local files_info
    local -a file_checks=()

    files_info=$(feature_artifact_marks "$feat_path" "|")
    IFS='|' read -ra file_checks <<< "$files_info"

    echo '<tr>' >> "$output_file"
    if [[ $row -eq 1 ]]; then
        echo "<td rowspan=\"${CTX_FEAT_COUNT}\"><strong>${CTX_RUN_ID}</strong></td>" >> "$output_file"
    fi

    if [[ "$is_anomaly" == "yes" ]]; then
        echo "<td class=\"anomaly\">❌异常：${feat_name}（$(anomaly_desc_for "$feat_name")）</td>" >> "$output_file"
    else
        echo "<td>${feat_name}</td>" >> "$output_file"
    fi

    local mark
    for mark in "${file_checks[@]}"; do
        echo "<td>${mark}</td>" >> "$output_file"
    done

    if [[ $row -eq 1 ]]; then
        echo "<td rowspan=\"${CTX_FEAT_COUNT}\">${CTX_CODE_MOD}</td>" >> "$output_file"
        echo "<td rowspan=\"${CTX_FEAT_COUNT}\">${CTX_TEST_NEW}</td>" >> "$output_file"
        echo "<td rowspan=\"${CTX_FEAT_COUNT}\">${CTX_STEPS}</td>" >> "$output_file"
        echo "<td rowspan=\"${CTX_FEAT_COUNT}\">${CTX_RESULT}</td>" >> "$output_file"
    fi
    echo '</tr>' >> "$output_file"
}

append_run_html_rows() {
    local run_id=$1
    local output_file=$2
    local row=0 feat_name feat_path is_anomaly

    load_run_context "$run_id"

    if [[ ! -d "$CTX_RUN_DIR" ]]; then
        append_missing_run_row "$run_id" "$output_file" "目录不存在: ${CTX_RUN_DIR}"
        return
    fi

    if ((${#CTX_FEAT_DIRS[@]} == 0)); then
        append_empty_features_row "$output_file"
        return
    fi

    for feat_name in "${CTX_FEAT_DIRS[@]}"; do
        row=$((row + 1))
        feat_path="$(feat_dir_for "$CTX_RUN_DIR" "$feat_name")"
        is_anomaly=$(is_anomaly_dir "$feat_name")
        append_feature_html_row "$output_file" "$row" "$feat_name" "$feat_path" "$is_anomaly"
    done
}

# -----------------------------------------------------------------------------
# HTML 报告
# -----------------------------------------------------------------------------
write_html_shell() {
    local output_file=$1

    cat > "$output_file" << 'HTMLEOF'
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>co-Mind-Omni Express Workflow 验证结果</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; }
        h2 { color: #666; margin-top: 30px; }
        table { border-collapse: collapse; width: 100%; margin: 10px 0; font-size: 12px; }
        th, td { border: 1px solid #ddd; padding: 6px; text-align: center; }
        th { background-color: #4a90d9; color: white; }
        .anomaly { color: red; font-weight: bold; background-color: #fff0f0; }
    </style>
</head>
<body>
HTMLEOF
}

write_html_table_head() {
    local output_file=$1

    echo '<table>' >> "$output_file"
    echo '<thead><tr>
        <th>运行次</th>
        <th>特性目录</th>
        <th>spec.md</th>
        <th>design.md</th>
        <th>tasks.md</th>
        <th>research.md</th>
        <th>quickstart.md</th>
        <th>data-model.md</th>
        <th>checklists<br/>requirements.md</th>
        <th>contracts<br/>api-contract.md</th>
        <th>.runs</th>
        <th>.omnispec<br/>state.json</th>
        <th>代码修改</th>
        <th>用例生成</th>
        <th>步骤详情</th>
        <th>结果</th>
    </tr></thead>' >> "$output_file"
    echo '<tbody>' >> "$output_file"
}

generate_html_report() {
    local output_file="$HTML_REPORT_FILE"
    local run_id

    write_html_shell "$output_file"

    echo "<h1>co-Mind-Omni Express Workflow 验证结果</h1>" >> "$output_file"
    echo "<p><strong>生成时间：</strong>$(date '+%Y-%m-%d %H:%M:%S')</p>" >> "$output_file"
    echo "<p><strong>项目：</strong>$PROJECT</p>" >> "$output_file"
    echo "<p><strong>数据来源：</strong>$(workflow_dir_for)/</p>" >> "$output_file"
    echo "<p><strong>检查轮次：</strong>${RUN_IDS[*]}</p>" >> "$output_file"
    echo "<h2>运行详细对比表</h2>" >> "$output_file"

    write_html_table_head "$output_file"

    for run_id in "${RUN_IDS[@]}"; do
        append_run_html_rows "$run_id" "$output_file"
    done

    echo '</tbody></table>' >> "$output_file"
    echo '</body></html>' >> "$output_file"

    echo ""
    echo "=============================================="
    echo "HTML 报告已生成: $output_file"
    echo "=============================================="
}

# -----------------------------------------------------------------------------
# 批量检查流程
# -----------------------------------------------------------------------------
print_check_header() {
    echo "=============================================="
    echo "Express Workflow 检查结果"
    echo "=============================================="
    echo "项目:     $PROJECT"
    echo "工作区:   $(workflow_dir_for)/"
    echo "检查编号: ${RUN_IDS[*]}"
    echo ""
}

run_check_batch() {
    local run_id

    print_check_header

    for run_id in "${RUN_IDS[@]}"; do
        print_run_check "$run_id" || true
    done

    echo "=============================================="
    if [[ "$ASSUME_YES" == true ]]; then
        generate_html_report
        return
    fi

    printf '是否生成 HTML 报告? [y/N] '
    read -r answer
    if [[ "$answer" == [yY] || "$answer" == [yY][eE][sS] ]]; then
        generate_html_report
    fi
}

# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------
usage() {
    cat <<EOF
Usage: sdd-workflow-batch-check-express.sh [options]

选项:
  -p, --project <path>    被测项目目录（用于推断副本目录名，默认: CLAUDE_WORKING_DIR 或当前目录）
  -w, --workspace <path>  工作区根目录（默认: ${DEFAULT_WORKSPACE}）
  -n, --count <n>         检查编号 1..n（与 --runs 互斥，默认 ${BATCH_COUNT}）
  --runs <spec>           指定检查编号（与 -n 互斥），如 1,3,5 或 1-5 或 1-3,7
  -y, --yes               终端检查后直接生成 HTML 报告，跳过确认
  -h, --help              显示帮助

环境变量:
  SDD_PROJECT      同 --project
  SDD_WORKSPACE    同 --workspace
  SDD_BATCH_COUNT  同 --count

说明:
  扫描工作区 express/{项目名}-{N}/，与 sdd-workflow-batch-run.sh 目录约定一致。
  每轮检查 changes/* 下 SDD 产出（spec/design/tasks 等）、.runs 状态、git 代码修改、
  测试用例与 metrics 步骤；异常特性目录（如 master、feature）会单独标注。
  终端输出完成后，默认询问是否生成 HTML 对比报告；报告写入当前目录 ${HTML_REPORT_FILE}。

  batch-run 补跑后，可用 --runs 仅检查失败轮次，例如:
    sdd-workflow-batch-run.sh express --runs 2,4,6
    sdd-workflow-batch-check-express.sh -p /path/to/project --runs 2,4,6 -y

示例:
  sdd-workflow-batch-check-express.sh -p /path/to/project
  sdd-workflow-batch-check-express.sh -p /path/to/project -n 5 -y
  sdd-workflow-batch-check-express.sh --workspace ${DEFAULT_WORKSPACE} --runs 2,4,6 -y
  SDD_BATCH_COUNT=3 sdd-workflow-batch-check-express.sh -p . -y
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

    while [[ $# -gt 0 ]]; do
        case "$1" in
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
            -y|--yes)
                ASSUME_YES=true
                shift
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

    if [[ -z "$PROJECT" ]]; then
        if [[ -n "${SDD_PROJECT:-}" ]]; then
            PROJECT="$SDD_PROJECT"
        else
            PROJECT="$(get_working_dir)"
        fi
    fi

    PROJECT="$(resolve_path "$PROJECT")"
    WORKSPACE_BASE="$(resolve_path "$WORKSPACE_BASE")"

    # 自动检测项目名：若工作区中已存在 "项目名-N" 目录，使用该项目名
    if [[ -z "${SDD_PROJECT:-}" && "$PROJECT" == "$(get_working_dir)" ]]; then
        local detected
        detected=$(auto_detect_project_name "$(workflow_dir_for)")
        if [[ -n "$detected" ]]; then
            PROJECT_NAME="$detected"
            echo "自动检测到项目名: $PROJECT_NAME"
        else
            PROJECT_NAME="$(basename "$PROJECT")"
            echo "警告: 未检测到工作区目录，使用当前目录名: $PROJECT_NAME"
        fi
    else
        PROJECT_NAME="$(basename "$PROJECT")"
    fi

    resolve_run_ids "${count_override:-$BATCH_COUNT}"
}

# -----------------------------------------------------------------------------
# 项目名自动检测（未指定 -p 时）
# -----------------------------------------------------------------------------
auto_detect_project_name() {
    local wf_dir="$1"
    local detected=""
    local entry name

    # 扫描 express/ 目录下形如 "项目名-N" 的目录
    for entry in "$wf_dir"/*-[0-9]*; do
        [[ -d "$entry" ]] || continue
        name="$(basename "$entry")"
        # 去掉末尾的 -N 数字部分得到项目名
        detected="${name%-*[0-9]}"
        # 处理末尾是纯数字的情况（如 "project-1" → "project"）
        if [[ "$detected" != "$name" ]]; then
            echo "$detected"
            return 0
        fi
    done
    return 1
}

# -----------------------------------------------------------------------------
# 入口
# -----------------------------------------------------------------------------
parse_args "$@"
run_check_batch

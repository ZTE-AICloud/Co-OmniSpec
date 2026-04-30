#!/usr/bin/env bash
# 测试并行处理脚本
# 测试get-next-batches.sh和update-batches-status.sh脚本的功能

set -e

# 创建测试环境
create_test_environment() {
    # 创建临时目录
    local test_dir
    test_dir=$(mktemp -d "/tmp/omnispec_test_XXXXXX")
    local cache_dir="$test_dir/.cache/reverse/interfaces"
    mkdir -p "$cache_dir"

    # 创建测试批次映射文件
    cat > "$cache_dir/batch-mapping.json" << 'EOF'
{
  "total_batches": 3,
  "batch_size": 3,
  "batches": [
    {"batch_number": 1, "batch_file": "batch-details-1.json", "status": "pending"},
    {"batch_number": 2, "batch_file": "batch-details-2.json", "status": "pending"},
    {"batch_number": 3, "batch_file": "batch-details-3.json", "status": "pending"}
  ]
}
EOF

    # 创建测试批次详细文件
    for i in {1..3}; do
        cat > "$cache_dir/batch-details-$i.json" << EOF
{
  "batch_number": $i,
  "files": ["/test/file${i}_1.java", "/test/file${i}_2.java"],
  "estimated_tokens": 10000,
  "complexity_score": 5.0,
  "status": "pending"
}
EOF
    done

    # 创建批次状态文件
    cat > "$cache_dir/interface_scanning-batch-status.json" << 'EOF'
{
  "version": "1.1",
  "stage": "interface_scanning",
  "total_items": 6,
  "batch_size": 20,
  "total_batches": 3,
  "processed_batches": 0,
  "current_batch": 0,
  "failed_batches": 0,
  "start_time": "",
  "last_update": "",
  "status": "initialized",
  "batch_mappings": [
    {"batch_number": 1, "batch_file": "batch-details-1.json", "status": "pending", "estimated_tokens": 10000},
    {"batch_number": 2, "batch_file": "batch-details-2.json", "status": "pending", "estimated_tokens": 10000},
    {"batch_number": 3, "batch_file": "batch-details-3.json", "status": "pending", "estimated_tokens": 10000}
  ]
}
EOF

    echo "$test_dir"
}

# 测试获取下一个批次脚本
test_get_next_batches() {
    local test_dir="$1"
    echo "测试 get-next-batches.sh 脚本..."

    local script_path="./get-next-batches.sh"
    if [[ ! -f "$script_path" ]]; then
        echo "错误: 脚本文件不存在 $script_path"
        return 1
    fi

    # 执行脚本
    local output
    output=$("$script_path" --repo-root "$test_dir" --batch-count 2 2>/dev/null)

    if [[ $? -ne 0 ]]; then
        echo "脚本执行失败: $output"
        return 1
    fi

    # 解析输出
    local batch_count
    batch_count=$(echo "$output" | jq 'length' 2>/dev/null)

    if [[ $? -ne 0 ]] || [[ -z "$batch_count" ]]; then
        echo "无法解析脚本输出"
        return 1
    fi

    echo "获取到 $batch_count 个批次:"
    echo "$output" | jq -c '.[]' | while read -r batch; do
        local batch_number
        batch_number=$(echo "$batch" | jq -r '.batch_number')
        local status
        status=$(echo "$batch" | jq -r '.status')
        echo "  批次 $batch_number: $status"
    done

    if [[ $batch_count -gt 0 ]]; then
        echo "✅ 获取批次测试通过"
        return 0
    else
        echo "❌ 获取批次测试失败"
        return 1
    fi
}

# 测试批量更新批次状态脚本
test_update_batches_status() {
    local test_dir="$1"
    echo "测试 update-batches-status.sh 脚本..."

    local script_path="./update-batches-status.sh"
    if [[ ! -f "$script_path" ]]; then
        echo "错误: 脚本文件不存在 $script_path"
        return 1
    fi

    # 准备更新数据
    local batch_updates='[{"batch_number": 1, "status": "processing"}, {"batch_number": 2, "status": "processing"}]'

    # 执行脚本
    local output
    output=$("$script_path" --repo-root "$test_dir" --batch-updates "$batch_updates")

    local exit_code=$?

    if [[ $exit_code -ne 0 ]]; then
        echo "脚本执行失败 (退出码: $exit_code): $output"
        return 1
    fi

    # 解析输出
    echo "更新结果: $output"

    # 验证更新是否成功
    local success_count
    success_count=$(echo "$output" | jq -r '.success' 2>/dev/null)

    if [[ $? -eq 0 ]] && [[ $success_count -gt 0 ]]; then
        echo "✅ 批次状态更新测试通过"
        return 0
    else
        echo "❌ 批次状态更新测试失败"
        return 1
    fi
}

# 清理测试环境
cleanup_test_environment() {
    local test_dir="$1"
    if [[ -d "$test_dir" ]]; then
        rm -rf "$test_dir"
        echo "已清理测试环境: $test_dir"
    fi
}

# 主函数
main() {
    echo "开始测试并行处理脚本..."

    # 创建测试环境
    local test_dir
    test_dir=$(create_test_environment)
    echo "已创建测试环境: $test_dir"

    local success1=false
    local success2=false

    # 切换到脚本目录
    local original_dir
    original_dir=$(pwd)
    cd "$(dirname "$0")" || exit 1

    # 确保脚本有执行权限
    chmod +x get-next-batches.sh update-batches-status.sh

    trap 'cleanup_test_environment "$test_dir"' EXIT

    # 测试获取批次脚本
    if test_get_next_batches "$test_dir"; then
        success1=true
    fi

    echo

    # 测试更新批次状态脚本
    if test_update_batches_status "$test_dir"; then
        success2=true
    fi

    # 恢复原始目录
    cd "$original_dir" || exit 1

    if [[ "$success1" == true && "$success2" == true ]]; then
        echo
        echo "🎉 所有测试通过!"
        return 0
    else
        echo
        echo "💥 部分测试失败!"
        return 1
    fi
}

# 执行主函数
main
#!/usr/bin/env bash
# 测试接口批处理功能脚本
# 验证interface-analyzer子Agent和批处理相关脚本的功能

set -e

# 创建测试环境
create_test_environment() {
    # 创建临时目录
    local test_dir
    test_dir=$(mktemp -d "/tmp/omnispec_interface_test_XXXXXX")
    local cache_dir="$test_dir/.cache/reverse/interfaces"
    local output_dir="$test_dir/omni-doc/specs/interfaces"
    mkdir -p "$cache_dir"
    mkdir -p "$output_dir"

    # 创建测试接口清单文件
    cat > "$cache_dir/interface-list.json" << 'EOF'
{
  "version": "1.0",
  "generated_at": "2026-01-15T10:30:00Z",
  "total_interfaces": 8,
  "interfaces": [
    {
      "interface_id": "API-001",
      "name": "getUserInfo",
      "interface_type": "RESTful API",
      "source_file": "/test/controllers/user.controller.js",
      "path_method": "/api/users/{id} GET",
      "processing_status": "pending"
    },
    {
      "interface_id": "API-002",
      "name": "createUser",
      "interface_type": "RESTful API",
      "source_file": "/test/controllers/user.controller.js",
      "path_method": "/api/users POST",
      "processing_status": "pending"
    },
    {
      "interface_id": "API-003",
      "name": "updateUser",
      "interface_type": "RESTful API",
      "source_file": "/test/controllers/user.controller.js",
      "path_method": "/api/users/{id} PUT",
      "processing_status": "pending"
    },
    {
      "interface_id": "API-004",
      "name": "deleteUser",
      "interface_type": "RESTful API",
      "source_file": "/test/controllers/user.controller.js",
      "path_method": "/api/users/{id} DELETE",
      "processing_status": "pending"
    },
    {
      "interface_id": "API-005",
      "name": "listUsers",
      "interface_type": "RESTful API",
      "source_file": "/test/controllers/user.controller.js",
      "path_method": "/api/users GET",
      "processing_status": "pending"
    },
    {
      "interface_id": "API-006",
      "name": "getUserProfile",
      "interface_type": "RESTful API",
      "source_file": "/test/controllers/profile.controller.js",
      "path_method": "/api/profile/{id} GET",
      "processing_status": "pending"
    },
    {
      "interface_id": "API-007",
      "name": "updateProfile",
      "interface_type": "RESTful API",
      "source_file": "/test/controllers/profile.controller.js",
      "path_method": "/api/profile/{id} PUT",
      "processing_status": "pending"
    },
    {
      "interface_id": "API-008",
      "name": "deleteProfile",
      "interface_type": "RESTful API",
      "source_file": "/test/controllers/profile.controller.js",
      "path_method": "/api/profile/{id} DELETE",
      "processing_status": "pending"
    }
  ]
}
EOF

    # 创建模板文件
    cat > "$test_dir/.infra/templates/reverse-interface-detail-template.md" << 'EOF'
# 接口文档：{{interface_name}}

## 基本信息
- **接口ID**: {{interface_id}}
- **接口名称**: {{interface_name}}
- **接口类型**: {{interface_type}}
- **所属文件**: {{source_file}}

## 接口描述
{{#description}}
{{description}}
{{/description}}
{{^description}}
（该接口暂无详细描述）
{{/description}}
EOF

    cat > "$test_dir/.infra/templates/reverse-interface-inventory-template.md" << 'EOF'
# 接口清单

## 概述
- 总接口数: {{total_interfaces}}
- 生成时间: {{generated_at}}

## 接口列表
{{#interfaces}}
- [{{interface_id}}]({{interface_id}}_{{name}}.md) - {{name}} ({{interface_type}})
{{/interfaces}}
EOF

    echo "$test_dir"
}

# 测试创建接口批次脚本
test_create_interface_batches() {
    local test_dir="$1"
    echo "测试 create_interface_batches.py 脚本..."

    local script_path="./create_interface_batches.py"
    if [[ ! -f "$script_path" ]]; then
        echo "错误: 脚本文件不存在 $script_path"
        return 1
    fi

    # 执行脚本
    local output
    output=$(python3 "$script_path" "$test_dir" 2>&1)
    local exit_code=$?

    if [[ $exit_code -ne 0 ]]; then
        echo "脚本执行失败 (退出码: $exit_code): $output"
        return 1
    fi

    # 验证生成的文件
    local cache_dir="$test_dir/.cache/reverse/interfaces"
    if [[ ! -f "$cache_dir/interface-batch-mapping.json" ]]; then
        echo "错误: 批次映射文件未生成"
        return 1
    fi

    if [[ ! -f "$cache_dir/interface_detail-batch-status.json" ]]; then
        echo "错误: 批次状态文件未生成"
        return 1
    fi

    # 检查批次详细文件
    local batch_count
    batch_count=$(jq -r '.total_batches' "$cache_dir/interface-batch-mapping.json")
    for ((i=1; i<=batch_count; i++)); do
        if [[ ! -f "$cache_dir/interface-batch-details-$i.json" ]]; then
            echo "错误: 批次详细文件 interface-batch-details-$i.json 未生成"
            return 1
        fi
    done

    echo "✅ 批次创建测试通过"
    echo "生成了 $batch_count 个批次"
    return 0
}

# 测试获取接口批次脚本
test_get_next_interface_batches() {
    local test_dir="$1"
    echo "测试 get_next_interface_batches.sh 脚本..."

    local script_path="./get_next_interface_batches.sh"
    if [[ ! -f "$script_path" ]]; then
        echo "错误: 脚本文件不存在 $script_path"
        return 1
    fi

    # 执行脚本
    local output
    output=$("$script_path" --repo-root "$test_dir" --batch-count 2 2>/dev/null)
    local exit_code=$?

    if [[ $exit_code -ne 0 ]]; then
        echo "脚本执行失败 (退出码: $exit_code): $output"
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

# 测试更新接口批次状态脚本
test_update_interface_batches_status() {
    local test_dir="$1"
    echo "测试 update_interface_batches_status.sh 脚本..."

    local script_path="./update_interface_batches_status.sh"
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
    echo "开始测试接口批处理功能..."

    # 创建测试环境
    local test_dir
    test_dir=$(create_test_environment)
    echo "已创建测试环境: $test_dir"

    local success1=false
    local success2=false
    local success3=false

    # 切换到脚本目录
    local original_dir
    original_dir=$(pwd)
    cd "$(dirname "$0")" || exit 1

    # 确保脚本有执行权限
    chmod +x get_next_interface_batches.sh update_interface_batches_status.sh

    trap 'cleanup_test_environment "$test_dir"' EXIT

    # 测试创建批次脚本
    if test_create_interface_batches "$test_dir"; then
        success1=true
    fi

    echo

    # 测试获取批次脚本
    if test_get_next_interface_batches "$test_dir"; then
        success2=true
    fi

    echo

    # 测试更新批次状态脚本
    if test_update_interface_batches_status "$test_dir"; then
        success3=true
    fi

    # 恢复原始目录
    cd "$original_dir" || exit 1

    if [[ "$success1" == true && "$success2" == true && "$success3" == true ]]; then
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
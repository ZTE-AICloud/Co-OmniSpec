#!/usr/bin/env pwsh
# 检查交互模式状态脚本
# 用于 AI Agent 判断是否需要用户确认

# 获取脚本所在目录
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# 加载公共函数
. "$scriptDir/common.ps1"

# 获取参数（从命令行参数或环境变量）
$args = if ($args.Count -gt 0) { $args[0] } else { $env:ARGUMENTS }

# 判断是否需要确认
if (Test-ShouldRequireConfirmation -Args $args) {
    Write-Output '{"interactive": true, "auto_confirm": false, "mode": "interactive"}'
} else {
    Write-Output '{"interactive": false, "auto_confirm": true, "mode": "auto"}'
}


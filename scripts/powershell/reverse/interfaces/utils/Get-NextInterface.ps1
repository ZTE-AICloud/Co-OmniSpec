# -*- coding: utf-8 -*-
#
# 获取下一个要处理的接口工具包装脚本 (PowerShell)
# 调用Python脚本获取下一个待处理的接口
#
# 使用方法:
#   .\Get-NextInterface.ps1 [-RepoRoot <String>]
#

param(
    [Parameter(Mandatory=$false)]
    [string]$RepoRoot = $(Get-Location)
)

# 设置错误处理偏好
$ErrorActionPreference = 'Stop'

# 获取脚本所在目录
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$PythonScript = Join-Path $ScriptDir "..\..\..\..\python\reverse_interfaces\get_next_interface.py" | Resolve-Path

# 检查Python脚本是否存在
if (-not (Test-Path $PythonScript)) {
    Write-Error "错误: Python脚本不存在: $PythonScript"
    exit 1
}

# 检查Python环境
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "错误: 未找到python命令"
    exit 1
}

# 验证仓库根目录
if (-not (Test-Path $RepoRoot)) {
    Write-Error "错误: 仓库根目录不存在: $RepoRoot"
    exit 1
}

# 转换为绝对路径
$RepoRoot = Resolve-Path $RepoRoot

# 执行Python脚本
try {
    python $PythonScript $RepoRoot
} catch {
    Write-Error "执行Python脚本时发生错误: $_"
    exit 1
}
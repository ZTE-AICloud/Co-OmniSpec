# -*- coding: utf-8 -*-
#
# 获取接口处理进度工具包装脚本 (PowerShell)
# 调用Python脚本获取接口处理进度
#
# 使用方法:
#   .\Get-ProcessingProgress.ps1 [-RepoRoot <String>] [-Format <String>]
#

param(
    [Parameter(Mandatory=$false)]
    [string]$RepoRoot = $(Get-Location),

    [Parameter(Mandatory=$false)]
    [ValidateSet("json", "text")]
    [string]$Format = "text"
)

# 设置错误处理偏好
$ErrorActionPreference = 'Stop'

# 获取脚本所在目录
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$PythonScript = Join-Path $ScriptDir "..\..\..\..\python\reverse_interfaces\get_processing_progress.py" | Resolve-Path

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
    if ($Format -eq "json") {
        python $PythonScript $RepoRoot --format json
    } else {
        python $PythonScript $RepoRoot
    }
} catch {
    Write-Error "执行Python脚本时发生错误: $_"
    exit 1
}
# -*- coding: utf-8 -*-
#
# 更新接口处理状态工具包装脚本 (PowerShell)
# 调用Python脚本更新接口处理状态
#
# 使用方法:
#   .\Update-InterfaceStatus.ps1 -InterfaceId <String> -Status <String> [-RepoRoot <String>]
#

param(
    [Parameter(Mandatory=$true)]
    [string]$InterfaceId,

    [Parameter(Mandatory=$true)]
    [ValidateSet("pending", "processing", "completed", "failed")]
    [string]$Status,

    [Parameter(Mandatory=$false)]
    [string]$RepoRoot = $(Get-Location)
)

# 设置错误处理偏好
$ErrorActionPreference = 'Stop'

# 获取脚本所在目录
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$PythonScript = Join-Path $ScriptDir "..\..\..\..\python\reverse_interfaces\update_interface_status.py" | Resolve-Path

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
    python $PythonScript $RepoRoot $InterfaceId $Status
} catch {
    Write-Error "执行Python脚本时发生错误: $_"
    exit 1
}
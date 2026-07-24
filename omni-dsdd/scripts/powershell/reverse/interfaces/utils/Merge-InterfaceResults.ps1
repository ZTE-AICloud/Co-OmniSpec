# -*- coding: utf-8 -*-
#
# 接口清单合并工具包装脚本 (PowerShell)
# 调用Python脚本执行接口清单批次合并
#
# 使用方法:
#   .\Merge-InterfaceResults.ps1 [-Verbose] [-Validate] [-Enhanced]
#

[CmdletBinding()]
param(
    [Parameter(Position=0)]
    [string]$RepoRoot = $(Get-Location),

    [switch]$Verbose,

    [switch]$Validate,

    [switch]$Enhanced,

    [switch]$Help
)

# 显示帮助信息
if ($Help) {
    Write-Host "使用方法: Merge-InterfaceResults.ps1 [-RepoRoot <path>] [-Verbose] [-Validate] [-Enhanced]"
    Write-Host ""
    Write-Host "参数:"
    Write-Host "  -RepoRoot <path>  仓库根目录路径 (可选，默认为当前目录)"
    Write-Host "  -Verbose          显示详细处理信息"
    Write-Host "  -Validate         验证合并结果"
    Write-Host "  -Enhanced         使用增强版脚本"
    Write-Host "  -Help             显示此帮助信息"
    exit 0
}

# 获取脚本所在目录
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$PythonScript = Join-Path $ScriptDir "..\..\..\..\python\merge_interface_results.py"
$EnhancedPythonScript = Join-Path $ScriptDir "..\..\..\..\python\merge_interface_results_enhanced.py"

# 检查Python脚本是否存在
if (-not (Test-Path $PythonScript)) {
    Write-Error "错误: Python脚本不存在: $PythonScript"
    exit 1
}

if (-not (Test-Path $EnhancedPythonScript)) {
    Write-Error "错误: 增强版Python脚本不存在: $EnhancedPythonScript"
    exit 1
}

# 检查Python环境
try {
    $PythonVersion = python --version 2>$null
    if (-not $PythonVersion) {
        $PythonVersion = python3 --version 2>$null
        if (-not $PythonVersion) {
            Write-Error "错误: 未找到python或python3命令"
            exit 1
        }
        $PythonCommand = "python3"
    } else {
        $PythonCommand = "python"
    }
} catch {
    Write-Error "错误: 未找到Python环境"
    exit 1
}

# 验证仓库根目录
if (-not (Test-Path $RepoRoot)) {
    Write-Error "错误: 仓库根目录不存在: $RepoRoot"
    exit 1
}

# 转换为绝对路径
$RepoRoot = Resolve-Path $RepoRoot

# 选择要使用的脚本
if ($Enhanced) {
    $ScriptToUse = $EnhancedPythonScript
    $ScriptName = "增强版接口清单合并工具"
} else {
    $ScriptToUse = $PythonScript
    $ScriptName = "接口清单合并工具"
}

# 构造Python脚本参数
$PythonArgs = @($RepoRoot)

if ($Verbose) {
    $PythonArgs += "--verbose"
}

if ($Validate) {
    $PythonArgs += "--validate"
}

# 执行合并
Write-Host "使用 $ScriptName 合并接口清单..."

try {
    if ($Verbose) {
        & $PythonCommand $ScriptToUse $PythonArgs
    } else {
        & $PythonCommand $ScriptToUse $PythonArgs 2>$null
    }

    if ($LASTEXITCODE -eq 0) {
        Write-Host "接口清单合并完成"
    } else {
        Write-Error "接口清单合并失败"
        exit 1
    }
} catch {
    Write-Error "执行Python脚本时发生错误: $_"
    exit 1
}
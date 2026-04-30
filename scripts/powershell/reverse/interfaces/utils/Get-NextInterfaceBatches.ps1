#!/usr/bin/env pwsh
# 获取下一个接口批次信息工具 (PowerShell版本)
# 调用Python脚本获取下一个待处理的接口批次
#
# 使用方法:
#   .\Get-NextInterfaceBatches.ps1 -RepoRoot <repo_root> [-BatchCount <count>]
#

param(
    [Parameter(Mandatory=$true)]
    [string]$RepoRoot,

    [Parameter(Mandatory=$false)]
    [int]$BatchCount = 5,

    [switch]$Help
)

# 显示帮助信息
function Show-Help {
    @"
使用方法:
    .\Get-NextInterfaceBatches.ps1 -RepoRoot <repo_root> [-BatchCount <count>]

参数:
    -RepoRoot: 仓库根目录路径
    -BatchCount: 要获取的批次数量（默认5）
    -Help: 显示此帮助信息
"@
}

# 如果请求帮助，显示帮助信息并退出
if ($Help) {
    Show-Help
    exit 0
}

# 验证仓库根目录
if (-not (Test-Path -Path $RepoRoot -PathType Container)) {
    Write-Error "错误: 仓库根目录不存在 $RepoRoot"
    exit 1
}

# 获取脚本目录
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$pythonScript = Join-Path -Path $scriptDir -ChildPath "..\..\..\..\..\python\reverse_interfaces\get_next_interface_batches.py" | Resolve-Path

# 检查Python脚本是否存在
if (-not (Test-Path -Path $pythonScript -PathType Leaf)) {
    Write-Error "错误: Python脚本不存在 $pythonScript"
    exit 1
}

# 执行Python脚本
try {
    $output = & python $pythonScript $RepoRoot --batch-count $BatchCount
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Python脚本执行失败: $output"
        exit 1
    }
    Write-Output $output
} catch {
    Write-Error "执行过程中发生错误: $_"
    exit 1
}
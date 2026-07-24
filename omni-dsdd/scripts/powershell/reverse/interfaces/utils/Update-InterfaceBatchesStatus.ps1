#!/usr/bin/env pwsh
# 批量更新接口批次状态工具 (PowerShell版本)
# 调用Python脚本批量更新接口批次状态
#
# 使用方法:
#   .\Update-InterfaceBatchesStatus.ps1 -RepoRoot <repo_root> -BatchUpdates "<batch_updates_json>"
#

param(
    [Parameter(Mandatory=$true)]
    [string]$RepoRoot,

    [Parameter(Mandatory=$true)]
    [string]$BatchUpdates,

    [switch]$Help
)

# 显示帮助信息
function Show-Help {
    @"
使用方法:
    .\Update-InterfaceBatchesStatus.ps1 -RepoRoot <repo_root> -BatchUpdates "<batch_updates_json>"

参数:
    -RepoRoot: 仓库根目录路径
    -BatchUpdates: 批次更新信息的JSON字符串，格式为 [{"batch_number": 1, "status": "completed"}, ...]
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
$pythonScript = Join-Path -Path $scriptDir -ChildPath "..\..\..\..\..\python\reverse_interfaces\update_interface_batches_status.py" | Resolve-Path

# 检查Python脚本是否存在
if (-not (Test-Path -Path $pythonScript -PathType Leaf)) {
    Write-Error "错误: Python脚本不存在 $pythonScript"
    exit 1
}

# 执行Python脚本
try {
    $output = & python $pythonScript $RepoRoot --batch-updates $BatchUpdates
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Python脚本执行失败: $output"
        exit 1
    }
    Write-Output $output
} catch {
    Write-Error "执行过程中发生错误: $_"
    exit 1
}
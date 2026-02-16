#!/usr/bin/env pwsh
# 接口扫描批次信息批量获取工具 (PowerShell版本)
# 在AI Agent批量处理批次时，获取要处理的多个批次信息

param(
    [Parameter(Mandatory=$true)]
    [string]$RepoRoot,

    [int]$BatchCount = 5,

    [switch]$Help
)

# 显示帮助信息
function Show-Help {
    @"
接口扫描批次信息批量获取工具 (PowerShell版本)
在AI Agent批量处理批次时，获取要处理的多个批次信息

使用方法:
    .\get-next-batches.ps1 -RepoRoot <repo_root> [-BatchCount <count>]

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

# 导入通用函数
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$commonScript = Join-Path -Path $scriptDir -ChildPath "common.ps1"
if (Test-Path -Path $commonScript -PathType Leaf) {
    . $commonScript
}

$cacheDir = Join-Path -Path $RepoRoot -ChildPath ".cache/omni-reverse/interfaces"

# 获取多个待处理的批次
function Get-NextPendingBatches {
    param([int]$BatchCount)

    $batchMappingFile = Join-Path -Path $cacheDir -ChildPath "batch-mapping.json"

    if (-not (Test-Path -Path $batchMappingFile -PathType Leaf)) {
        Write-Error "错误: 批次映射文件不存在 $batchMappingFile"
        return @()
    }

    try {
        $batchMapping = Get-Content -Path $batchMappingFile -Raw | ConvertFrom-Json

        # 查找多个状态为pending的批次
        $pendingBatches = @()
        foreach ($batchInfo in $batchMapping.batches) {
            if ($batchInfo.status -eq "pending" -and $pendingBatches.Count -lt $BatchCount) {
                $pendingBatches += $batchInfo
            }
        }

        # 如果没有找到足够的pending批次，查找状态为initialized的批次作为补充
        if ($pendingBatches.Count -lt $BatchCount) {
            foreach ($batchInfo in $batchMapping.batches) {
                if ($batchInfo.status -eq "initialized" -and $pendingBatches.Count -lt $BatchCount) {
                    $pendingBatches += $batchInfo
                }
            }
        }

        return $pendingBatches
    } catch {
        Write-Error "错误: 无法读取批次映射文件: $_"
        return @()
    }
}

# 主函数
function Main {
    # 获取多个待处理的批次
    $batches = Get-NextPendingBatches -BatchCount $BatchCount
    $batches | ConvertTo-Json -Depth 10
}

# 执行主函数
Main
#!/usr/bin/env pwsh
# 接口扫描批次信息获取工具 (PowerShell版本)
# 在AI Agent循环处理批次时，获取要处理的批次信息

param(
    [Parameter(Mandatory=$true)]
    [string]$RepoRoot,

    [Parameter(Mandatory=$true)]
    [ValidateSet("get-next-batch", "update-batch-status", "get-batch-info", "get-summary")]
    [string]$Action,

    [int]$BatchNumber,

    [string]$Status,

    [switch]$Help
)

# 显示帮助信息
function Show-Help {
    @"
接口扫描批次信息获取工具 (PowerShell版本)
在AI Agent循环处理批次时，获取要处理的批次信息

使用方法:
    .\get-next-batch.ps1 -RepoRoot <repo_root> -Action <action> [-BatchNumber <number>] [-Status <status>]

参数:
    -RepoRoot: 仓库根目录路径
    -Action: 操作类型（get-next-batch, update-batch-status, get-batch-info, get-summary）
    -BatchNumber: 批次编号（用于更新状态或获取信息时）
    -Status: 批次状态（用于更新状态时）
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

# 获取下一个待处理的批次
function Get-NextPendingBatch {
    $batchMappingFile = Join-Path -Path $cacheDir -ChildPath "batch-mapping.json"

    if (-not (Test-Path -Path $batchMappingFile -PathType Leaf)) {
        Write-Error "错误: 批次映射文件不存在 $batchMappingFile"
        return @{}
    }

    try {
        $batchMapping = Get-Content -Path $batchMappingFile -Raw | ConvertFrom-Json

        # 查找第一个状态为pending的批次
        foreach ($batchInfo in $batchMapping.batches) {
            if ($batchInfo.status -eq "pending") {
                return $batchInfo
            }
        }

        # 如果没有找到pending的批次，查找状态为initialized的批次
        foreach ($batchInfo in $batchMapping.batches) {
            if ($batchInfo.status -eq "initialized") {
                return $batchInfo
            }
        }

        # 没有找到待处理的批次
        return @{}
    } catch {
        Write-Error "错误: 无法读取批次映射文件: $_"
        return @{}
    }
}

# 更新批次状态
function Update-BatchStatus {
    param(
        [int]$BatchNumber,
        [string]$Status
    )

    $updated = $false
    $timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

    # 更新批次映射文件
    $batchMappingFile = Join-Path -Path $cacheDir -ChildPath "batch-mapping.json"
    if (Test-Path -Path $batchMappingFile -PathType Leaf) {
        try {
            $batchMapping = Get-Content -Path $batchMappingFile -Raw | ConvertFrom-Json

            foreach ($batchInfo in $batchMapping.batches) {
                if ($batchInfo.batch_number -eq $BatchNumber) {
                    $batchInfo.status = $Status
                    $batchInfo.last_updated = $timestamp
                    $updated = $true
                    break
                }
            }

            if ($updated) {
                $batchMapping | ConvertTo-Json -Depth 10 | Set-Content -Path $batchMappingFile -Encoding UTF8
            }
        } catch {
            Write-Warning "警告: 无法更新批次映射文件: $_"
        }
    }

    # 更新批次详细文件
    $batchDetailsFile = Join-Path -Path $cacheDir -ChildPath "batch-details-$BatchNumber.json"
    if (Test-Path -Path $batchDetailsFile -PathType Leaf) {
        try {
            $batchDetails = Get-Content -Path $batchDetailsFile -Raw | ConvertFrom-Json
            $batchDetails.status = $Status
            $batchDetails.last_updated = $timestamp
            $batchDetails | ConvertTo-Json -Depth 10 | Set-Content -Path $batchDetailsFile -Encoding UTF8
        } catch {
            Write-Warning "警告: 无法更新批次详细文件: $_"
        }
    }

    # 更新批次状态文件
    $batchStatusFile = Join-Path -Path $cacheDir -ChildPath "interface_scanning-batch-status.json"
    if (Test-Path -Path $batchStatusFile -PathType Leaf) {
        try {
            $batchStatus = Get-Content -Path $batchStatusFile -Raw | ConvertFrom-Json

            # 更新总体状态
            switch ($Status) {
                "completed" {
                    $batchStatus.processed_batches = ($batchStatus.processed_batches + 1)
                    $batchStatus.current_batch = $BatchNumber
                }
                "failed" {
                    $batchStatus.failed_batches = ($batchStatus.failed_batches + 1)
                }
            }

            $batchStatus.last_update = $timestamp

            # 更新批次映射信息
            if ($batchStatus.PSObject.Properties.Name -contains "batch_mappings") {
                foreach ($batchMapping in $batchStatus.batch_mappings) {
                    if ($batchMapping.batch_number -eq $BatchNumber) {
                        $batchMapping.status = $Status
                        break
                    }
                }
            }

            $batchStatus | ConvertTo-Json -Depth 10 | Set-Content -Path $batchStatusFile -Encoding UTF8
        } catch {
            Write-Warning "警告: 无法更新批次状态文件: $_"
        }
    }

    # 输出结果
    @{
        success = $updated
        batch_number = $BatchNumber
        status = $Status
    } | ConvertTo-Json -Compress
}

# 获取指定批次的详细信息
function Get-BatchInfo {
    param([int]$BatchNumber)

    $batchDetailsFile = Join-Path -Path $cacheDir -ChildPath "batch-details-$BatchNumber.json"

    if (-not (Test-Path -Path $batchDetailsFile -PathType Leaf)) {
        Write-Error "错误: 批次详细文件不存在 $batchDetailsFile"
        return @{}
    }

    try {
        $batchInfo = Get-Content -Path $batchDetailsFile -Raw | ConvertFrom-Json
        return $batchInfo
    } catch {
        Write-Error "错误: 无法读取批次详细文件: $_"
        return @{}
    }
}

# 获取批次处理摘要
function Get-BatchSummary {
    $summary = @{
        total_batches = 0
        pending_batches = 0
        completed_batches = 0
        failed_batches = 0
        processing_batches = 0
    }

    # 读取批次映射文件
    $batchMappingFile = Join-Path -Path $cacheDir -ChildPath "batch-mapping.json"
    if (Test-Path -Path $batchMappingFile -PathType Leaf) {
        try {
            $batchMapping = Get-Content -Path $batchMappingFile -Raw | ConvertFrom-Json
            $summary.total_batches = $batchMapping.total_batches

            foreach ($batchInfo in $batchMapping.batches) {
                switch ($batchInfo.status) {
                    "pending" { $summary.pending_batches++ }
                    "completed" { $summary.completed_batches++ }
                    "failed" { $summary.failed_batches++ }
                    "processing" { $summary.processing_batches++ }
                }
            }
        } catch {
            Write-Warning "警告: 无法读取批次映射文件: $_"
        }
    }

    return $summary
}

# 主函数
function Main {
    switch ($Action) {
        "get-next-batch" {
            $batchInfo = Get-NextPendingBatch
            $batchInfo | ConvertTo-Json -Depth 10
        }

        "update-batch-status" {
            if ($BatchNumber -eq 0 -or [string]::IsNullOrEmpty($Status)) {
                Write-Error "错误: 更新批次状态需要提供 -BatchNumber 和 -Status 参数"
                exit 1
            }
            Update-BatchStatus -BatchNumber $BatchNumber -Status $Status
        }

        "get-batch-info" {
            if ($BatchNumber -eq 0) {
                Write-Error "错误: 获取批次信息需要提供 -BatchNumber 参数"
                exit 1
            }
            $batchInfo = Get-BatchInfo -BatchNumber $BatchNumber
            $batchInfo | ConvertTo-Json -Depth 10
        }

        "get-summary" {
            $summary = Get-BatchSummary
            $summary | ConvertTo-Json -Compress
        }
    }
}

# 执行主函数
Main
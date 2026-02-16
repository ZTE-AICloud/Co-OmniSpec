#!/usr/bin/env pwsh
# 批量更新接口扫描批次状态工具 (PowerShell版本)
# 批量更新多个批次的处理状态

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
批量更新接口扫描批次状态工具 (PowerShell版本)
批量更新多个批次的处理状态

使用方法:
    .\update-batches-status.ps1 -RepoRoot <repo_root> -BatchUpdates "<batch_updates_json>"

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

# 导入通用函数
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$commonScript = Join-Path -Path $scriptDir -ChildPath "common.ps1"
if (Test-Path -Path $commonScript -PathType Leaf) {
    . $commonScript
}

$cacheDir = Join-Path -Path $RepoRoot -ChildPath ".cache/omni-reverse/interfaces"
$timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

# 更新单个批次状态
function Update-SingleBatchStatus {
    param(
        [int]$BatchNumber,
        [string]$Status
    )

    $updated = $false
    $result = @{
        batch_number = $BatchNumber
        status = $Status
        success = $false
    }

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

    $result.success = $updated
    return $result
}

# 批量更新批次状态
function Update-BatchesStatus {
    param([string]$BatchUpdates)

    # 验证JSON格式
    try {
        $updates = $BatchUpdates | ConvertFrom-Json
    } catch {
        Write-Error "错误: 无效的JSON格式: $_"
        exit 1
    }

    # 检查是否为数组
    if ($updates -isnot [array]) {
        Write-Error "错误: 批次更新信息必须是数组格式"
        exit 1
    }

    # 初始化结果数组
    $results = @()
    $successCount = 0
    $failedCount = 0

    # 遍历所有批次更新
    foreach ($updateItem in $updates) {
        $batchNumber = $updateItem.batch_number
        $status = $updateItem.status

        # 验证必需字段
        if ($null -eq $batchNumber -or $null -eq $status) {
            $results += @{
                batch_number = $batchNumber
                error = "缺少批次编号或状态"
                success = $false
            }
            $failedCount++
            continue
        }

        # 验证状态
        $validStatuses = @("pending", "processing", "completed", "failed")
        if ($validStatuses -notcontains $status) {
            $results += @{
                batch_number = $batchNumber
                error = "无效的状态 '$status'"
                success = $false
            }
            $failedCount++
            continue
        }

        # 更新批次状态
        $result = Update-SingleBatchStatus -BatchNumber $batchNumber -Status $status
        if ($result.success) {
            $results += $result
            $successCount++
        } else {
            $results += @{
                batch_number = $batchNumber
                error = "未找到指定的批次"
                success = $false
            }
            $failedCount++
        }
    }

    # 输出最终结果
    $finalResult = @{
        success = $successCount
        failed = $failedCount
        details = $results
    }

    $finalResult | ConvertTo-Json -Depth 10

    # 如果有任何失败，返回非零退出码
    if ($failedCount -gt 0) {
        exit 1
    }
}

# 主函数
function Main {
    Update-BatchesStatus -BatchUpdates $BatchUpdates
}

# 执行主函数
Main
#!/usr/bin/env pwsh
# 批次完成状态验证工具 (PowerShell版本)
# 验证批次是否真正完成，包括状态文件、输出文件和时间戳验证

$ErrorActionPreference = 'Stop'

# 初始化变量
$RepoRoot = ""
$BatchNumbers = ""
$StageType = ""
$OutputPattern = ""

# 显示帮助信息
function Show-Help {
    Write-Host @"
批次完成状态验证工具 (PowerShell版本)
验证批次是否真正完成，包括状态文件、输出文件和时间戳验证

使用方法:
    .\verify-batches-completion.ps1 -RepoRoot <repo_root> -BatchNumbers '<batch_numbers_json>' [-StageType <stage_type>] [-OutputPattern <pattern>]

参数:
    -RepoRoot: 仓库根目录路径
    -BatchNumbers: 批次编号数组的JSON字符串，格式为 [1, 2, 3]
    -StageType: 阶段类型（scenarios/interfaces/functions/call-chain/function-identification），用于确定缓存目录和状态文件名
    -OutputPattern: 输出文件模式，如 "scenario-list-batch-{batch_number}.json"（可选，会根据stage-type自动推断）
    -Help, -h: 显示此帮助信息

示例:
    .\verify-batches-completion.ps1 -RepoRoot "C:\path\to\repo" -BatchNumbers '[1,2,3]' -StageType scenarios
"@
}

# 解析命令行参数
$paramArgs = $args
for ($i = 0; $i -lt $paramArgs.Length; $i++) {
    switch ($paramArgs[$i]) {
        "-RepoRoot" {
            $RepoRoot = $paramArgs[++$i]
        }
        "-BatchNumbers" {
            $BatchNumbers = $paramArgs[++$i]
        }
        "-StageType" {
            $StageType = $paramArgs[++$i]
        }
        "-OutputPattern" {
            $OutputPattern = $paramArgs[++$i]
        }
        "-Help" { Show-Help; exit 0 }
        "-h" { Show-Help; exit 0 }
        default {
            Write-Error "未知参数: $($paramArgs[$i])"
            Show-Help
            exit 1
        }
    }
}

# 验证必需参数
if ([string]::IsNullOrEmpty($RepoRoot) -or [string]::IsNullOrEmpty($BatchNumbers)) {
    Write-Error "错误: 必须提供 -RepoRoot 和 -BatchNumbers 参数"
    Show-Help
    exit 1
}

# 验证仓库根目录
if (-not (Test-Path -Path $RepoRoot -PathType Container)) {
    Write-Error "错误: 仓库根目录不存在 $RepoRoot"
    exit 1
}

# 导入通用函数
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $ScriptDir "common.ps1")

# 根据阶段类型确定缓存目录和状态文件名
function Get-CacheInfo {
    param([string]$StageType)

    $cacheDir = ""
    $statusFile = ""
    $outputPattern = ""

    switch ($StageType) {
        "scenarios" {
            $cacheDir = Join-Path $RepoRoot ".cache\omni-reverse\scenarios"
            $statusFile = "scenario_scanning-batch-status.json"
            $outputPattern = "scenario-list-batch-{batch_number}.json"
        }
        "interfaces" {
            $cacheDir = Join-Path $RepoRoot ".cache\omni-reverse\interfaces"
            $statusFile = "interface_scanning-batch-status.json"
            $outputPattern = "interface-list-batch-{batch_number}.json"
        }
        "call-chain" {
            $cacheDir = Join-Path $RepoRoot ".cache\omni-reverse\functions\call-chain-analysis"
            $statusFile = "call_chain_analysis-batch-status.json"
            $outputPattern = "call-chains-batch-{batch_number}.json"
        }
        "function-identification" {
            $cacheDir = Join-Path $RepoRoot ".cache\omni-reverse\functions\function-identification"
            $statusFile = "function_identification-batch-status.json"
            $outputPattern = "functions-batch-{batch_number}.json"
        }
        "test-case-analysis" {
            $cacheDir = Join-Path $RepoRoot ".cache\omni-reverse\functions\test-case-analysis"
            $statusFile = "test_case_analysis-batch-status.json"
            $outputPattern = "test-cases-analysis-batch-{batch_number}.json"
        }
        default {
            # 默认使用interfaces（向后兼容）
            $cacheDir = Join-Path $RepoRoot ".cache\omni-reverse\interfaces"
            $statusFile = "interface_scanning-batch-status.json"
            $outputPattern = "interface-list-batch-{batch_number}.json"
        }
    }

    return @{
        CacheDir = $cacheDir
        StatusFile = $statusFile
        OutputPattern = $outputPattern
    }
}

# 验证批次是否完成
function Test-BatchCompletion {
    param(
        [int]$BatchNumber,
        [string]$CacheDir,
        [string]$StatusFile,
        [string]$OutputPattern
    )

    # 替换输出文件模式中的 {batch_number}
    $outputFile = $OutputPattern -replace '\{batch_number\}', $BatchNumber
    $outputFilePath = Join-Path $CacheDir $outputFile

    # 1. 检查批次状态文件中的状态
    $batchStatusFile = Join-Path $CacheDir $StatusFile
    $statusInFile = ""
    $lastUpdated = ""

    if (Test-Path -Path $batchStatusFile -PathType Leaf) {
        try {
            $batchStatus = Get-Content -Path $batchStatusFile -Raw | ConvertFrom-Json

            # 从批次状态文件中查找批次状态
            if ($batchStatus.batch_mappings) {
                $batchMapping = $batchStatus.batch_mappings | Where-Object { $_.batch_number -eq $BatchNumber }
                if ($batchMapping) {
                    $statusInFile = $batchMapping.status
                }
            }
        } catch {
            # 忽略错误，继续检查其他文件
        }
    }

    # 如果batch_mappings中没有，尝试从batch-mapping.json中查找
    if ([string]::IsNullOrEmpty($statusInFile)) {
        $batchMappingFile = Join-Path $CacheDir "batch-mapping.json"
        if (Test-Path -Path $batchMappingFile -PathType Leaf) {
            try {
                $batchMapping = Get-Content -Path $batchMappingFile -Raw | ConvertFrom-Json
                $batchInfo = $batchMapping.batches | Where-Object { $_.batch_number -eq $BatchNumber }
                if ($batchInfo) {
                    $statusInFile = $batchInfo.status
                    $lastUpdated = $batchInfo.last_updated
                }
            } catch {
                # 忽略错误
            }
        }
    }

    # 2. 检查输出文件是否存在
    $outputFileExists = $false
    $outputFileValid = $false
    if (Test-Path -Path $outputFilePath -PathType Leaf) {
        $outputFileExists = $true
        # 验证JSON格式
        try {
            $null = Get-Content -Path $outputFilePath -Raw | ConvertFrom-Json
            $outputFileValid = $true
        } catch {
            $outputFileValid = $false
        }
    }

    # 3. 检查批次详细文件中的状态
    $batchDetailsFile = Join-Path $CacheDir "batch-details-$BatchNumber.json"
    $statusInDetails = ""
    if (Test-Path -Path $batchDetailsFile -PathType Leaf) {
        try {
            $batchDetails = Get-Content -Path $batchDetailsFile -Raw | ConvertFrom-Json
            $statusInDetails = $batchDetails.status
            if ([string]::IsNullOrEmpty($lastUpdated)) {
                $lastUpdated = $batchDetails.last_updated
            }
        } catch {
            # 忽略错误
        }
    }

    # 4. 验证时间戳（如果存在）
    $timestampValid = $true
    if (-not [string]::IsNullOrEmpty($lastUpdated)) {
        # 检查时间戳格式是否为ISO 8601
        if ($lastUpdated -notmatch '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z?$') {
            $timestampValid = $false
        }
    }

    # 5. 综合判断批次是否完成
    $isCompleted = $false
    $completionReason = ""

    # 状态必须为"completed"
    if ($statusInFile -eq "completed" -or $statusInDetails -eq "completed") {
        # 输出文件必须存在且有效
        if ($outputFileExists -and $outputFileValid) {
            $isCompleted = $true
            $completionReason = "状态为completed且输出文件存在且有效"
        } else {
            $completionReason = "状态为completed但输出文件不存在或无效"
        }
    } else {
        if ([string]::IsNullOrEmpty($statusInFile) -and [string]::IsNullOrEmpty($statusInDetails)) {
            $completionReason = "未找到批次状态信息"
        } else {
            $status = if (-not [string]::IsNullOrEmpty($statusInFile)) { $statusInFile } else { $statusInDetails }
            $completionReason = "状态为'$status'，不是completed"
        }
    }

    # 构建结果对象
    return @{
        batch_number = $BatchNumber
        completed = $isCompleted
        reason = $completionReason
        status_in_file = $statusInFile
        status_in_details = $statusInDetails
        output_file_exists = $outputFileExists
        output_file_valid = $outputFileValid
        timestamp_valid = $timestampValid
        output_file_path = $outputFilePath
    }
}

# 主函数
function Main {
    # 确定缓存目录和状态文件
    $cacheInfo = Get-CacheInfo -StageType $StageType
    $cacheDir = $cacheInfo.CacheDir
    $statusFile = $cacheInfo.StatusFile
    $defaultOutputPattern = $cacheInfo.OutputPattern

    # 使用用户指定的输出模式或默认模式
    $outputPattern = if ([string]::IsNullOrEmpty($OutputPattern)) { $defaultOutputPattern } else { $OutputPattern }

    # 验证批次编号JSON格式
    try {
        $batchNumbersArray = $BatchNumbers | ConvertFrom-Json
        if ($batchNumbersArray -isnot [Array]) {
            Write-Error "错误: 批次编号必须是数组格式"
            exit 1
        }
    } catch {
        Write-Error "错误: 无效的批次编号JSON格式: $_"
        exit 1
    }

    # 初始化结果数组
    $results = @()
    $allCompleted = $true
    $completedCount = 0
    $totalCount = 0

    # 遍历所有批次编号
    foreach ($batchNumber in $batchNumbersArray) {
        if ($null -eq $batchNumber) {
            continue
        }

        $totalCount++

        # 验证批次完成状态
        $result = Test-BatchCompletion -BatchNumber $batchNumber -CacheDir $cacheDir -StatusFile $statusFile -OutputPattern $outputPattern

        if ($result.completed) {
            $completedCount++
        } else {
            $allCompleted = $false
        }

        # 添加到结果数组
        $results += $result
    }

    # 构建最终结果
    $finalResult = @{
        all_completed = $allCompleted
        completed_count = $completedCount
        total_count = $totalCount
        batches = $results
    }

    # 输出JSON结果
    $finalResult | ConvertTo-Json -Depth 10

    # 如果有未完成的批次，返回非零退出码
    if (-not $allCompleted) {
        exit 1
    }
}

# 执行主函数
Main


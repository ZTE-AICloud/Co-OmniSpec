#!/usr/bin/env pwsh
# 场景扫描批次生成工具 (PowerShell版本)
# 基于AI Agent的各种规则过滤后，把要检索的文件基于文件数量进行分批，生成批次文件

param(
    [Parameter(Mandatory=$true)]
    [string]$RepoRoot,

    [Parameter(Mandatory=$true)]
    [string]$FileList,

    [int]$BatchSize = 20,

    [int]$MaxTokens = 150000,

    [switch]$Help
)

# 显示帮助信息
function Show-Help {
    @"
场景扫描批次生成工具 (PowerShell版本)
基于AI Agent的各种规则过滤后，把要检索的文件基于文件数量进行分批，生成批次文件

使用方法:
    .\generate-scenario-batches.ps1 -RepoRoot <repo_root> -FileList <file_list_json> [-BatchSize <size>] [-MaxTokens <tokens>]

参数:
    -RepoRoot: 仓库根目录路径
    -FileList: 要处理的文件列表（JSON格式）
    -BatchSize: 每批文件数量（可选，默认20）
    -MaxTokens: 每批最大Token数（可选，默认150000）
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

# 验证文件列表文件
if (-not (Test-Path -Path $FileList -PathType Leaf)) {
    Write-Error "错误: 文件列表文件不存在 $FileList"
    exit 1
}

# 估算文件的Token数量
function Estimate-TokensForFile {
    param([string]$FilePath)

    # 检查文件是否存在
    if (-not (Test-Path -Path $FilePath -PathType Leaf)) {
        return 1000  # 保守估计
    }

    try {
        # 计算行数并估算tokens（每行约5个tokens）
        $lineCount = (Get-Content -Path $FilePath | Measure-Object).Count
        return ($lineCount * 5)
    } catch {
        return 1000  # 保守估计
    }
}

# 从JSON文件中提取文件列表
function Extract-FileList {
    param([string]$FileListPath)

    try {
        $data = Get-Content -Path $FileListPath -Raw | ConvertFrom-Json

        # 支持多种格式的文件列表
        if ($data -is [array]) {
            return $data
        } elseif ($data.PSObject.Properties.Name -contains "files") {
            return $data.files
        } else {
            throw "Invalid file list format"
        }
    } catch {
        Write-Error "错误: 无法从 $FileListPath 中提取文件列表: $_"
        throw
    }
}

# 主函数
function Main {
    Write-Output "开始生成场景扫描批次..."

    # 提取文件列表
    try {
        $files = Extract-FileList -FileListPath $FileList
        $fileCount = $files.Count
        Write-Output "找到 $fileCount 个文件需要处理"

        if ($fileCount -eq 0) {
            Write-Warning "警告: 文件列表为空"
            exit 0
        }
    } catch {
        exit 1
    }

    # 创建缓存目录
    $cacheDir = Join-Path -Path $RepoRoot -ChildPath ".cache/omni-reverse/scenarios"
    if (-not (Test-Path -Path $cacheDir -PathType Container)) {
        New-Item -ItemType Directory -Path $cacheDir -Force | Out-Null
    }

    # 创建批次
    $batchNumber = 1
    $currentBatchFiles = @()
    $currentTokens = 0
    $batchMappings = @()
    $totalBatches = 0

    # 处理每个文件
    foreach ($filePath in $files) {
        # 估算文件Token数量
        $fileTokens = Estimate-TokensForFile -FilePath $filePath

        # 检查是否需要创建新批次
        if (($currentBatchFiles.Count -ge $BatchSize) -or
            (($currentTokens + $fileTokens) -gt $MaxTokens -and $currentBatchFiles.Count -gt 0)) {

            # 创建当前批次
            $batchFileName = "batch-details-$batchNumber.json"
            $batchFilePath = Join-Path -Path $cacheDir -ChildPath $batchFileName

            # 创建批次对象
            $batchInfo = @{
                batch_number = $batchNumber
                files = $currentBatchFiles
                estimated_tokens = $currentTokens
                complexity_score = [Math]::Floor($currentTokens / 1000)
                status = "pending"
            }

            # 保存批次文件
            $batchInfo | ConvertTo-Json -Depth 10 | Set-Content -Path $batchFilePath -Encoding UTF8
            Write-Output "已创建批次文件: $batchFilePath"

            # 添加到映射列表
            $batchMappings += @{
                batch_number = $batchNumber
                batch_file = $batchFileName
                status = "pending"
                estimated_tokens = $currentTokens
            }

            # 重置批次
            $currentBatchFiles = @()
            $currentTokens = 0
            $batchNumber++
        }

        # 添加文件到当前批次
        $currentBatchFiles += $filePath
        $currentTokens += $fileTokens
    }

    # 处理最后一个批次
    if ($currentBatchFiles.Count -gt 0) {
        $batchFileName = "batch-details-$batchNumber.json"
        $batchFilePath = Join-Path -Path $cacheDir -ChildPath $batchFileName

        # 创建批次对象
        $batchInfo = @{
            batch_number = $batchNumber
            files = $currentBatchFiles
            estimated_tokens = $currentTokens
            complexity_score = [Math]::Floor($currentTokens / 1000)
            status = "pending"
        }

        # 保存批次文件
        $batchInfo | ConvertTo-Json -Depth 10 | Set-Content -Path $batchFilePath -Encoding UTF8
        Write-Output "已创建批次文件: $batchFilePath"

        # 添加到映射列表
        $batchMappings += @{
            batch_number = $batchNumber
            batch_file = $batchFileName
            status = "pending"
            estimated_tokens = $currentTokens
        }

        $batchNumber++
    }

    $totalBatches = $batchNumber - 1
    Write-Output "创建了 $totalBatches 个批次"

    # 创建批次映射文件
    $batchMappingFile = Join-Path -Path $cacheDir -ChildPath "batch-mapping.json"
    $batchMapping = @{
        total_batches = $totalBatches
        batch_size = $BatchSize
        batches = $batchMappings
    }

    $batchMapping | ConvertTo-Json -Depth 10 | Set-Content -Path $batchMappingFile -Encoding UTF8
    Write-Output "已创建批次映射文件: $batchMappingFile"

    # 初始化批次状态文件
    $batchStatusFile = Join-Path -Path $cacheDir -ChildPath "scenario_scanning-batch-status.json"
    $batchStatus = @{
        version = "1.1"
        stage = "scenario_scanning"
        total_items = $fileCount
        batch_size = $BatchSize
        total_batches = $totalBatches
        processed_batches = 0
        current_batch = 0
        failed_batches = 0
        start_time = ""
        last_update = ""
        status = "initialized"
        batch_mappings = @()
    }

    $batchStatus | ConvertTo-Json -Depth 10 | Set-Content -Path $batchStatusFile -Encoding UTF8
    Write-Output "已初始化批次状态文件: $batchStatusFile"
    Write-Output "批次生成完成，总共创建了 $totalBatches 个批次"
}

# 执行主函数
Main


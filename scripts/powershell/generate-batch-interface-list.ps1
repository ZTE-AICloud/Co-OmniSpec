#!/usr/bin/env pwsh
# 生成批次接口清单工具
# 从临时文件中读取接口数据，合并生成批次接口清单文件
#
# 用法:
#   generate-batch-interface-list.ps1 -RepoRoot <仓库根目录> -BatchNumber <批次编号>
#
# 参数:
#   -RepoRoot: 仓库根目录路径
#   -BatchNumber: 批次编号

param(
    [Parameter(Mandatory=$true)]
    [string]$RepoRoot,
    
    [Parameter(Mandatory=$true)]
    [int]$BatchNumber,
    
    [switch]$Help
)

$ErrorActionPreference = 'Stop'

function Write-Error-Log {
    param([string]$Message)
    Write-Error "[ERROR] $Message"
}

function Write-Info-Log {
    param([string]$Message)
    Write-Output "[INFO] $Message"
}

# 显示帮助信息
if ($Help) {
    Write-Output "用法: $PSCommandPath -RepoRoot <仓库根目录> -BatchNumber <批次编号>"
    exit 0
}

# 验证仓库根目录
if (-not (Test-Path -Path $RepoRoot -PathType Container)) {
    Write-Error-Log "仓库根目录不存在: $RepoRoot"
    exit 1
}

# 验证批次编号
if ($BatchNumber -lt 1) {
    Write-Error-Log "批次编号必须大于0: $BatchNumber"
    exit 1
}

# 设置路径
$CacheDir = Join-Path -Path $RepoRoot -ChildPath ".cache/reverse/interfaces"
$TempDir = Join-Path -Path $CacheDir -ChildPath "temp"
$BatchDetailsFile = Join-Path -Path $CacheDir -ChildPath "batch-details-${BatchNumber}.json"
$OutputFile = Join-Path -Path $CacheDir -ChildPath "interface-list-batch-${BatchNumber}.json"

# 验证批次详情文件是否存在
if (-not (Test-Path -Path $BatchDetailsFile -PathType Leaf)) {
    Write-Error-Log "批次详情文件不存在: $BatchDetailsFile"
    exit 1
}

# 获取总批次数
function Get-TotalBatches {
    $totalBatches = 0
    
    # 先从batch-details获取
    try {
        $batchDetails = Get-Content -Path $BatchDetailsFile -Raw | ConvertFrom-Json
        if ($batchDetails.PSObject.Properties.Name -contains "total_batches") {
            $totalBatches = $batchDetails.total_batches
        }
    } catch {
        # 忽略错误，继续尝试从batch-mapping获取
    }
    
    # 如果为0，尝试从batch-mapping获取
    if ($totalBatches -eq 0) {
        $batchMappingFile = Join-Path -Path $CacheDir -ChildPath "batch-mapping.json"
        if (Test-Path -Path $batchMappingFile -PathType Leaf) {
            try {
                $batchMapping = Get-Content -Path $batchMappingFile -Raw | ConvertFrom-Json
                if ($batchMapping.PSObject.Properties.Name -contains "total_batches") {
                    $totalBatches = $batchMapping.total_batches
                }
            } catch {
                Write-Error-Log "无法读取批次映射文件: $_"
            }
        }
    }
    
    return $totalBatches
}

# 收集临时文件
function Get-TempFiles {
    if (-not (Test-Path -Path $TempDir -PathType Container)) {
        return @()
    }
    
    $prefix = "interface-${BatchNumber}-"
    $tempFiles = @()
    
    # 查找匹配的临时文件
    $files = Get-ChildItem -Path $TempDir -Filter "${prefix}*.json" -File
    foreach ($file in $files) {
        $tempFiles += $file.FullName
    }
    
    # 按文件索引排序
    $tempFiles = $tempFiles | Sort-Object {
        $basename = [System.IO.Path]::GetFileNameWithoutExtension($_)
        $indexStr = $basename -replace "^interface-${BatchNumber}-", ""
        [int]$indexStr
    }
    
    return $tempFiles
}

# 验证接口数据
function Test-InterfaceValid {
    param([PSCustomObject]$Interface)
    
    $requiredFields = @('name', 'interface_type', 'source_file')
    
    foreach ($field in $requiredFields) {
        if (-not ($Interface.PSObject.Properties.Name -contains $field)) {
            return $false
        }
    }
    
    return $true
}

# 合并接口数据
function Merge-Interfaces {
    param([string[]]$TempFiles)
    
    $allInterfaces = @()
    $interfaceIndex = 1
    
    foreach ($tempFile in $TempFiles) {
        if (-not (Test-Path -Path $tempFile -PathType Leaf)) {
            continue
        }
        
        try {
            $tempData = Get-Content -Path $tempFile -Raw | ConvertFrom-Json
            
            # 支持两种格式
            $interfaces = @()
            if ($tempData -is [array]) {
                $interfaces = $tempData
            } elseif ($tempData.PSObject.Properties.Name -contains "interfaces") {
                $interfaces = $tempData.interfaces
            } else {
                Write-Warning "临时文件格式不正确 $tempFile，跳过"
                continue
            }
            
            # 处理每个接口
            foreach ($interface in $interfaces) {
                # 验证接口数据
                if (-not (Test-InterfaceValid -Interface $interface)) {
                    Write-Warning "接口数据无效，跳过: $tempFile"
                    continue
                }
                
                # 生成interface_id
                $interfaceId = "API-${BatchNumber}-{0:D3}" -f $interfaceIndex
                
                # 创建接口对象
                $interfaceObj = [PSCustomObject]@{
                    interface_id = $interfaceId
                    name = $interface.name
                    business_name = if ($interface.PSObject.Properties.Name -contains "business_name") { $interface.business_name } else { "" }
                    business_domain = if ($interface.PSObject.Properties.Name -contains "business_domain") { $interface.business_domain } else { "" }
                    business_function = if ($interface.PSObject.Properties.Name -contains "business_function") { $interface.business_function } else { "" }
                    interface_type = $interface.interface_type
                    source_file = $interface.source_file
                    path_method = if ($interface.PSObject.Properties.Name -contains "path_method") { $interface.path_method } else { "" }
                    parameters = if ($interface.PSObject.Properties.Name -contains "parameters") { $interface.parameters } else { @() }
                    returns = if ($interface.PSObject.Properties.Name -contains "returns") { $interface.returns } else { @{} }
                    description = if ($interface.PSObject.Properties.Name -contains "description") { $interface.description } else { "" }
                    module = if ($interface.PSObject.Properties.Name -contains "module") { $interface.module } else { "" }
                    layer = if ($interface.PSObject.Properties.Name -contains "layer") { $interface.layer } else { "" }
                    language = if ($interface.PSObject.Properties.Name -contains "language") { $interface.language } else { "" }
                    confidence = if ($interface.PSObject.Properties.Name -contains "confidence") { $interface.confidence } else { 0.0 }
                    tags = if ($interface.PSObject.Properties.Name -contains "tags") { $interface.tags } else { @() }
                    annotations = if ($interface.PSObject.Properties.Name -contains "annotations") { $interface.annotations } else { @() }
                }
                
                $allInterfaces += $interfaceObj
                $interfaceIndex++
            }
        } catch {
            Write-Warning "无法处理临时文件 $tempFile : $_，跳过"
            continue
        }
    }
    
    return $allInterfaces
}

# 主处理逻辑
function Main {
    Write-Info-Log "开始生成批次 ${BatchNumber} 的接口清单..."
    
    # 获取总批次数
    $TotalBatches = Get-TotalBatches
    if ($TotalBatches -eq 0) {
        Write-Error-Log "无法获取总批次数"
        exit 1
    }
    
    # 收集临时文件
    $TempFiles = Get-TempFiles
    
    if ($TempFiles.Count -eq 0) {
        Write-Info-Log "警告: 未找到批次 ${BatchNumber} 的临时文件，生成空清单"
        $AllInterfaces = @()
    } else {
        Write-Info-Log "找到 $($TempFiles.Count) 个临时文件"
        
        # 合并接口数据
        $AllInterfaces = Merge-Interfaces -TempFiles $TempFiles
    }
    
    # 生成批次接口清单
    $GeneratedAt = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    
    $BatchInterfaceList = [PSCustomObject]@{
        batch_number = $BatchNumber
        total_batches = $TotalBatches
        generated_at = $GeneratedAt
        interfaces = $AllInterfaces
    }
    
    # 确保输出目录存在
    $OutputDir = Split-Path -Path $OutputFile -Parent
    if (-not (Test-Path -Path $OutputDir -PathType Container)) {
        New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
    }
    
    # 保存批次接口清单文件
    $BatchInterfaceList | ConvertTo-Json -Depth 10 | Set-Content -Path $OutputFile -Encoding UTF8
    
    Write-Info-Log "成功生成批次接口清单: $OutputFile"
    Write-Info-Log "包含 $($AllInterfaces.Count) 个接口"
}

# 执行主函数
Main


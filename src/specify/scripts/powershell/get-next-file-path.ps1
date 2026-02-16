#!/usr/bin/env pwsh
# 从批次文件中获取下一个要处理的文件路径
#
# 用法:
#   get-next-file-path.ps1 -BatchFile <批次文件路径> -FileIndex <文件索引> -RepoRoot <仓库根目录>
#
# 参数:
#   -BatchFile: 批次文件路径（如 batch-details-3.json）
#   -FileIndex: 文件在批次中的索引（从0开始），如果为-1则自动查找下一个未处理的文件
#   -RepoRoot: 仓库根目录路径
#
# 输出:
#   输出文件的绝对路径（如果成功）
#   如果失败，输出错误信息到stderr并返回非零退出码

$ErrorActionPreference = 'Stop'

param(
    [Parameter(Mandatory=$true)]
    [string]$BatchFile,
    
    [Parameter(Mandatory=$true)]
    [int]$FileIndex,
    
    [Parameter(Mandatory=$true)]
    [string]$RepoRoot
)

function Write-Error {
    param([string]$Message)
    [Console]::Error.WriteLine("[ERROR] $Message")
}

# 验证仓库根目录
if (-not (Test-Path -Path $RepoRoot -PathType Container)) {
    Write-Error "仓库根目录不存在: $RepoRoot"
    exit 1
}

# 验证批次文件是否存在
if (-not (Test-Path -Path $BatchFile -PathType Leaf)) {
    Write-Error "批次文件不存在: $BatchFile"
    exit 1
}

try {
    # 读取批次文件
    $batchContent = Get-Content -Path $BatchFile -Raw -Encoding UTF8
    $batchData = $batchContent | ConvertFrom-Json
    
    # 验证批次数据结构
    if (-not $batchData.PSObject.Properties.Name -contains "files") {
        Write-Error "批次文件中缺少 'files' 字段: $BatchFile"
        exit 1
    }
    
    $files = $batchData.files
    
    if ($files -isnot [array]) {
        Write-Error "批次文件中的 'files' 字段不是数组: $BatchFile"
        exit 1
    }
    
    # 如果 FileIndex 为 -1，自动查找下一个未处理的文件（且文件存在）
    if ($FileIndex -eq -1) {
        $relativeFilePath = $null
        $repoRootPath = Resolve-Path -Path $RepoRoot
        
        foreach ($fileEntry in $files) {
            $tempRelativePath = $null
            $shouldProcess = $false
            
            if ($fileEntry -is [PSCustomObject] -or $fileEntry -is [hashtable]) {
                # 新格式：对象包含 path 和 status
                $fileStatus = $fileEntry.status
                if ($fileStatus -ne "completed" -and $fileStatus -ne "failed") {
                    $tempRelativePath = $fileEntry.path
                    $shouldProcess = $true
                }
            } elseif ($fileEntry -is [string]) {
                # 旧格式：直接是字符串，默认未处理
                $tempRelativePath = $fileEntry
                $shouldProcess = $true
            }
            
            if ($shouldProcess -and $null -ne $tempRelativePath -and $tempRelativePath -ne "") {
                # 检查文件是否存在
                try {
                    $tempAbsolutePath = Join-Path -Path $repoRootPath -ChildPath $tempRelativePath
                    $tempAbsolutePath = [System.IO.Path]::GetFullPath($tempAbsolutePath)
                    
                    if (Test-Path -Path $tempAbsolutePath -PathType Leaf) {
                        $relativeFilePath = $tempRelativePath
                        break
                    }
                } catch {
                    # 路径解析失败，跳过并继续查找下一个
                    continue
                }
            }
        }
        
        if ($null -eq $relativeFilePath -or $relativeFilePath -eq "") {
            Write-Error "批次中没有未处理且存在的文件"
            exit 1
        }
    } else {
        # 检查索引是否有效
        if ($FileIndex -lt 0 -or $FileIndex -ge $files.Count) {
            Write-Error "文件索引 $FileIndex 超出范围 [0, $($files.Count - 1)]"
            exit 1
        }
        
        # 获取文件路径（支持新旧格式）
        $fileEntry = $files[$FileIndex]
        
        if ($fileEntry -is [PSCustomObject] -or $fileEntry -is [hashtable]) {
            # 新格式：对象包含 path 字段
            $relativeFilePath = $fileEntry.path
            if ($null -eq $relativeFilePath -or $relativeFilePath -eq "") {
                Write-Error "文件对象中缺少 path 字段: 索引 $FileIndex"
                exit 1
            }
        } elseif ($fileEntry -is [string]) {
            # 旧格式：直接是字符串
            $relativeFilePath = $fileEntry
        } else {
            Write-Error "文件条目格式无效: 索引 $FileIndex"
            exit 1
        }
        
        if ($null -eq $relativeFilePath -or $relativeFilePath -eq "") {
            Write-Error "文件路径为空或无效: 索引 $FileIndex"
            exit 1
        }
    }
    
    # 转换为绝对路径
    $repoRootPath = Resolve-Path -Path $RepoRoot
    $absoluteFilePath = Join-Path -Path $repoRootPath -ChildPath $relativeFilePath
    $absoluteFilePath = [System.IO.Path]::GetFullPath($absoluteFilePath)
    
    # 验证文件是否存在
    if (-not (Test-Path -Path $absoluteFilePath -PathType Leaf)) {
        Write-Error "文件不存在: $absoluteFilePath (相对路径: $relativeFilePath)"
        exit 1
    }
    
    # 输出绝对路径
    Write-Output $absoluteFilePath
    exit 0
    
} catch {
    Write-Error "处理批次文件时发生错误: $_"
    exit 1
}


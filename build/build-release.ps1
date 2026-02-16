#!/usr/bin/env pwsh

# OmniSpec 发布构建脚本 (Windows/PowerShell 版本)
# 功能：为所有类型和 agent 组合执行构建

$ErrorActionPreference = 'Stop'

# 显示使用说明
function Show-Usage {
    $scriptName = if ($PSCommandPath) { Split-Path -Leaf $PSCommandPath } else { "build-release.ps1" }
    Write-Host @"
OmniSpec 发布构建脚本

使用方法:
  .\$scriptName [选项]

功能说明:
  为所有 agent（cursor, claude, codex, flow）执行构建（Windows 构建，使用 install.ps1）
  路径规则：默认路径为 release，二级目录为 agent 名（如 flow），不再嵌套 OmniSpecVersion 层
  默认行为：构建前不会清理输出目录（使用 -CleanOutput 参数才会清理）

选项:
  -h, --help             显示此帮助信息
  -v, --version <版本>  指定版本号（默认：v1.0.0），必须为三段式格式：vX.Y.Z（如：v1.0.0, v2.1.3）
  -o, --output <路径>    指定基础输出路径（默认：release），完整路径为：<基础路径>/release/<agent>
  --clean, --remove      压缩完成后删除构建目录（默认不删除）
  -CleanOutput           清理输出目录（默认不清理）
  --ai-ide               启用 AI-IDE 版本后置处理，重组目录结构为 AI-IDE 格式

示例:
  # 执行所有组合的构建（默认不清理输出目录）
  .\$scriptName

  # 指定版本号
  .\$scriptName -Version v2.0.0
  .\$scriptName -Version v1.5.3 -Output C:\tmp\publish

  # 指定基础输出路径（默认：release）
  .\$scriptName -Output C:\tmp\publish
  .\$scriptName -Output .\custom-output

  # 执行构建并删除构建目录
  .\$scriptName -Clean

  # 清理输出目录
  .\$scriptName -CleanOutput

  # 组合使用
  .\$scriptName -Version v2.0.0 -Output C:\tmp\publish -Clean
  .\$scriptName -Version v1.5.3 -Output .\custom-output -CleanOutput -Clean

  # 启用 AI-IDE 版本后置处理
  .\$scriptName --ai-ide
  .\$scriptName -Version v2.0.0 --ai-ide

"@
}

# 获取脚本所在目录
$SCRIPT_DIR = Split-Path -Parent $PSCommandPath
$BUILD_SCRIPT = Join-Path $SCRIPT_DIR "build.ps1"
$DEFAULT_BASE_OUTPUT_DIR = Split-Path -Parent $SCRIPT_DIR

# 颜色输出函数
function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Green
}

function Write-Warn {
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# 验证版本号格式（三段式：vX.Y.Z）
function Test-Version {
    param([string]$Version)
    
    # 检查格式：必须以 v 开头，后跟三段数字，用点分隔
    if ($Version -notmatch '^v\d+\.\d+\.\d+$') {
        Write-Error "版本号格式错误: $Version"
        Write-Error "版本号必须为三段式格式：vX.Y.Z（如：v1.0.0, v2.1.3）"
        return $false
    }
    
    return $true
}

# 生成 agent 的完整输出路径
# 格式：<base_path>/release/<agent>
function Get-AgentOutputPath {
    param(
        [string]$BasePath,
        [string]$Version,
        [string]$Agent
    )
    
    $fullPath = Join-Path $BasePath "release"
    $fullPath = Join-Path $fullPath $Agent
    
    # 转换为绝对路径
    if ([System.IO.Path]::IsPathRooted($fullPath)) {
        return $fullPath
    } else {
        try {
            $resolvedPath = Resolve-Path -Path $fullPath -ErrorAction Stop
            return $resolvedPath.Path
        } catch {
            # 如果路径不存在，返回绝对路径
            $currentDir = (Get-Location).Path
            return (Join-Path $currentDir $fullPath)
        }
    }
}

# 检查 build.ps1 是否存在
function Test-BuildScript {
    if (-not (Test-Path $BUILD_SCRIPT)) {
        Write-Error "build.ps1 脚本不存在: $BUILD_SCRIPT"
        exit 1
    }
}

# 清理输出目录
function Clear-OutputDirectory {
    param([string]$OutputDir)
    
    if (-not (Test-Path $OutputDir)) {
        Write-Info "输出目录不存在，无需清理: $OutputDir"
        return
    }
    
    # 检查目录是否为空
    $items = Get-ChildItem -Path $OutputDir -Force -ErrorAction SilentlyContinue
    if ($null -eq $items -or $items.Count -eq 0) {
        Write-Info "输出目录为空，无需清理: $OutputDir"
        return
    }
    
    Write-Warn "正在清理输出目录: $OutputDir"
    Write-Warn "此操作将删除目录下的所有文件和文件夹"
    
    # 统计要删除的文件数量
    $fileCount = (Get-ChildItem -Path $OutputDir -Force -ErrorAction SilentlyContinue).Count
    Write-Info "将删除 $fileCount 个项目"
    
    # 删除目录下的所有内容
    Remove-Item -Path "$OutputDir\*" -Recurse -Force -ErrorAction SilentlyContinue
    Get-ChildItem -Path $OutputDir -Force -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '^\..*' } | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    
    # 验证清理结果
    $remainingItems = Get-ChildItem -Path $OutputDir -Force -ErrorAction SilentlyContinue
    if ($null -eq $remainingItems -or $remainingItems.Count -eq 0) {
        Write-Info "输出目录清理完成"
    } else {
        Write-Error "输出目录清理失败，仍有文件残留"
        exit 1
    }
}

# 执行单个构建
function Invoke-Build {
    param(
        [string]$Agent,
        [string]$BaseOutputPath,
        [bool]$CleanFlag,
        [string]$Version
    )
    
    # 生成 agent 的完整输出路径
    $agentOutputPath = Get-AgentOutputPath -BasePath $BaseOutputPath -Version $Version -Agent $Agent
    
    Write-Info "=========================================="
    Write-Info "构建: agent=$Agent, version=$Version"
    Write-Info "输出路径: $agentOutputPath"
    Write-Info "=========================================="
    
    # 构建命令参数
    $buildArgs = @(
        $Agent,
        "--version", $Version,
        "--output", $agentOutputPath
    )
    
    if ($CleanFlag) {
        $buildArgs += "--clean"
    }
    
    # 直接调用 build.ps1
    try {
        & $BUILD_SCRIPT $buildArgs
        if ($LASTEXITCODE -ne 0 -and -not $?) {
            Write-Error "构建失败: agent=$Agent, version=$Version"
            return $false
        }
    } catch {
        Write-Error "无法执行构建脚本: $_.Exception.Message"
        Write-Error "构建失败: agent=$Agent, version=$Version"
        return $false
    }
    
    Write-Info "构建成功: agent=$Agent, version=$Version"
    
    Write-Host ""
    return $true
}

# AI-IDE 版本后置处理：重组目录结构
# 从 release/<agent>/omnispec-<版本>-<agent>-<timestamp>/
# 转换为 release/<agent>/omnispec-<版本>/
function Reorganize-ForAiIde {
    param(
        [string]$BaseOutputDir,
        [string]$Version
    )
    
    $sourceDir = Join-Path $BaseOutputDir "release"
    $targetBaseDir = Join-Path $BaseOutputDir "release"
    
    Write-Info "=========================================="
    Write-Info "开始 AI-IDE 版本后置处理"
    Write-Info "源目录: $sourceDir"
    Write-Info "目标基础目录: $targetBaseDir"
    Write-Info "=========================================="
    Write-Host ""
    
    # 检查源目录是否存在
    if (-not (Test-Path $sourceDir)) {
        Write-Error "源目录不存在: $sourceDir"
        return $false
    }
    
    # 定义 agent 列表
    $agents = @("cursor", "claude", "codex", "flow")
    
    # 遍历每个 agent
    foreach ($agent in $agents) {
        $agentSourceDir = Join-Path $sourceDir $agent
        $agentTargetDir = Join-Path $targetBaseDir $agent
        
        # 检查 agent 源目录是否存在
        if (-not (Test-Path $agentSourceDir)) {
            Write-Warn "Agent 源目录不存在，跳过: $agentSourceDir"
            continue
        }
        
        Write-Info "处理 agent: $agent"
        Write-Info "  源目录: $agentSourceDir"
        Write-Info "  目标目录: $agentTargetDir"
        
        # 查找匹配的目录：omnispec-<version>-<agent>-<timestamp>
        # 例如：omnispec-v1.0.0-claude-20251207204358
        # 注意：build.ps1 生成的目录名包含完整的版本号（包含 v 前缀）
        $pattern = "omnispec-${Version}-${agent}-*"
        
        # 查找匹配的目录（-Filter 参数支持通配符）
        $foundDirs = Get-ChildItem -Path $agentSourceDir -Directory -Filter $pattern -ErrorAction SilentlyContinue
        
        if ($null -eq $foundDirs -or $foundDirs.Count -eq 0) {
            Write-Warn "  未找到匹配的目录: $pattern"
            continue
        }
        
        # 如果找到多个目录，使用第一个（通常只有一个）
        $sourceBuildDir = $foundDirs[0].FullName
        $dirName = $foundDirs[0].Name
        # 新目录名：omnispec-<version>（去掉时间戳部分，保留完整版本号包含 v 前缀）
        # 例如：omnispec-v1.0.0-claude-20251207204358 -> omnispec-v1.0.0
        $newDirName = "omnispec-${Version}"
        $tempDir = Join-Path $agentSourceDir $newDirName
        
        Write-Info "  找到构建目录: $dirName"
        Write-Info "  新目录名: $newDirName"
        
        # 重命名目录（去掉时间戳部分）
        if ($dirName -ne $newDirName) {
            if (Test-Path $tempDir) {
                Write-Warn "  目标目录已存在，先删除: $tempDir"
                Remove-Item -Path $tempDir -Recurse -Force
            }
            Write-Info "  重命名目录: $dirName -> $newDirName"
            Move-Item -Path $sourceBuildDir -Destination $tempDir
        } else {
            $tempDir = $sourceBuildDir
        }
        
        # 创建目标 agent 目录
        try {
            if (-not (Test-Path $agentTargetDir)) {
                New-Item -ItemType Directory -Path $agentTargetDir -Force | Out-Null
            }
        } catch {
            Write-Error "  无法创建目标目录: $agentTargetDir"
            Write-Error $_.Exception.Message
            continue
        }
        
        # 移动重命名后的目录到目标位置
        $finalTargetDir = Join-Path $agentTargetDir $newDirName
        if ($tempDir -ne $finalTargetDir) {
            if (Test-Path $finalTargetDir) {
                Write-Warn "  目标目录已存在，先删除: $finalTargetDir"
                Remove-Item -Path $finalTargetDir -Recurse -Force
            }
            Write-Info "  移动目录到: $finalTargetDir"
            Move-Item -Path $tempDir -Destination $finalTargetDir
        } else {
            Write-Info "  目录已在目标位置: $finalTargetDir"
        }
        
        # 移动 zip 文件（如果存在）
        # zip 文件名格式：omnispec-<version>-<agent>-<timestamp>.zip
        $zipPattern = "omnispec-${Version}-${agent}-*.zip"
        $zipFiles = Get-ChildItem -Path $agentSourceDir -File -Filter $zipPattern -ErrorAction SilentlyContinue
        
        if ($null -ne $zipFiles -and $zipFiles.Count -gt 0) {
            foreach ($zipFile in $zipFiles) {
                $zipName = $zipFile.Name
                $zipTarget = Join-Path $agentTargetDir $zipName
                Write-Info "  移动 zip 文件: $zipName"
                Move-Item -Path $zipFile.FullName -Destination $zipTarget
            }
        }
        
        Write-Info "  Agent $agent 处理完成"
        Write-Host ""
    }
    
    # 清理空的源目录结构
    Write-Info "清理空的源目录结构..."
    if (Test-Path $sourceDir) {
        # 检查是否所有 agent 目录都为空或不存在
        $allEmpty = $true
        foreach ($agent in $agents) {
            $agentDir = Join-Path $sourceDir $agent
            if ((Test-Path $agentDir) -and ((Get-ChildItem -Path $agentDir -Force -ErrorAction SilentlyContinue | Measure-Object).Count -gt 0)) {
                $allEmpty = $false
                break
            }
        }
        
        if ($allEmpty) {
            Write-Info "删除空的源目录: $sourceDir"
            Remove-Item -Path $sourceDir -Recurse -Force
        } else {
            Write-Warn "源目录仍包含文件，保留: $sourceDir"
        }
    }
    
    Write-Info "AI-IDE 版本后置处理完成"
    Write-Host ""
    return $true
}

# 获取并准备基础输出目录
function Get-BaseOutputDirectory {
    param([string]$BaseOutputPath)
    
    # 如果未指定基础输出路径，使用默认路径
    if ([string]::IsNullOrEmpty($BaseOutputPath)) {
        $BaseOutputPath = $DEFAULT_BASE_OUTPUT_DIR
    }
    
    # 先尝试创建目录
    Write-Info "准备基础输出路径: $BaseOutputPath"
    try {
        if (-not (Test-Path $BaseOutputPath)) {
            New-Item -ItemType Directory -Path $BaseOutputPath -Force | Out-Null
        }
        
        # 验证目录是否真的存在
        if (-not (Test-Path $BaseOutputPath -PathType Container)) {
            Write-Error "基础输出路径创建失败或不是目录: $BaseOutputPath"
            exit 1
        }
        
        # 转换为绝对路径
        $absPath = (Resolve-Path -Path $BaseOutputPath -ErrorAction Stop).Path
        
        # 如果目录是新创建的，给出提示
        $items = Get-ChildItem -Path $absPath -Force -ErrorAction SilentlyContinue
        if ($null -eq $items -or $items.Count -eq 0) {
            Write-Info "基础输出目录已创建: $absPath"
        } else {
            Write-Info "基础输出目录已存在: $absPath"
        }
        
        return $absPath
    } catch {
        Write-Error "无法创建或访问基础输出路径: $BaseOutputPath"
        Write-Error $_.Exception.Message
        exit 1
    }
}

# 主函数
function Main {
    param([string[]]$Arguments)
    
    # 解析参数
    $cleanBuildDir = $false
    $cleanOutput = $false  # 默认不清理输出目录
    $baseOutputPath = ""
    $version = "v1.0.0"  # 默认版本号为 v1.0.0
    $aiIdeMode = $false  # AI-IDE 模式标志
    
    # 解析所有参数
    for ($i = 0; $i -lt $Arguments.Length; $i++) {
        $arg = $Arguments[$i]
        
        switch ($arg) {
            { $_ -in '-h', '--help' } {
                Show-Usage
                exit 0
            }
            { $_ -in '-v', '--version' } {
                if ($i + 1 -ge $Arguments.Length) {
                    Write-Error "--version 选项需要指定版本号"
                    Write-Error "使用 '$PSCommandPath -h' 或 '$PSCommandPath --help' 查看详细使用说明"
                    exit 1
                }
                $nextVersion = $Arguments[++$i]
                if (-not (Test-Version -Version $nextVersion)) {
                    exit 1
                }
                $version = $nextVersion
            }
            { $_ -in '-o', '--output' } {
                if ($i + 1 -ge $Arguments.Length) {
                    Write-Error "--output 选项需要指定基础路径"
                    Write-Error "使用 '$PSCommandPath -h' 或 '$PSCommandPath --help' 查看详细使用说明"
                    exit 1
                }
                $baseOutputPath = $Arguments[++$i]
            }
            { $_ -in '--clean', '--remove' } {
                $cleanBuildDir = $true
            }
            { $_ -in '-CleanOutput', '--clean-output' } {
                $cleanOutput = $true
            }
            { $_ -eq '--ai-ide' } {
                $aiIdeMode = $true
            }
            default {
                Write-Error "未知参数: $arg"
                Write-Error "使用 '$PSCommandPath -h' 或 '$PSCommandPath --help' 查看详细使用说明"
                exit 1
            }
        }
    }
    
    Write-Host "=========================================="
    Write-Host "  OmniSpec 发布构建脚本"
    Write-Host "=========================================="
    Write-Host ""
    
    # 检查 build.ps1 是否存在
    Test-BuildScript
    
    # 验证版本号格式
    if (-not (Test-Version -Version $version)) {
        exit 1
    }
    
    # 获取并准备基础输出目录（如果不存在会自动创建）
    $BASE_OUTPUT_DIR = Get-BaseOutputDirectory -BaseOutputPath $baseOutputPath
    Write-Info "基础输出目录: $BASE_OUTPUT_DIR"
    Write-Info "版本号: $version"
    Write-Info "路径规则: $BASE_OUTPUT_DIR\release\<agent>"
    Write-Host ""
    
    # 如果指定了清理输出目录，先清理当前版本的目录
    if ($cleanOutput) {
        $cleanAgents = @("cursor", "claude", "codex", "flow")
        foreach ($agent in $cleanAgents) {
            $agentDir = Join-Path $BASE_OUTPUT_DIR "release" | Join-Path -ChildPath $agent
            if (Test-Path $agentDir) {
                Write-Warn "清理 agent 目录: $agentDir"
                Remove-Item -Path $agentDir -Recurse -Force
                Write-Info "已清理: $agentDir"
            }
        }
        Write-Host ""
    }
    
    # 定义 agent 列表
    $agents = @("cursor", "claude", "codex", "flow")
    
    # 统计信息
    $totalBuilds = $agents.Count
    $successCount = 0
    $failCount = 0
    
    Write-Info "开始执行发布构建..."
    Write-Info "构建数量: $totalBuilds"
    Write-Host ""
    
    # 遍历所有 agent
    foreach ($agent in $agents) {
        if (Invoke-Build -Agent $agent -BaseOutputPath $BASE_OUTPUT_DIR -CleanFlag $cleanBuildDir -Version $version) {
            $successCount++
        } else {
            $failCount++
        }
    }
    
    Write-Host ""
    Write-Host "=========================================="
    Write-Info "发布构建完成！"
    Write-Host "=========================================="
    Write-Host ""
    Write-Info "总构建数: $totalBuilds"
    Write-Info "成功: $successCount"
    if ($failCount -gt 0) {
        Write-Error "失败: $failCount"
    } else {
        Write-Info "失败: $failCount"
    }
    Write-Host ""
    
    # 如果启用了 AI-IDE 模式，执行后置处理
    if ($aiIdeMode) {
        Write-Host ""
        if (Reorganize-ForAiIde -BaseOutputDir $BASE_OUTPUT_DIR -Version $version) {
            Write-Info "AI-IDE 版本后置处理成功完成"
            Write-Info "重组后的路径: $BASE_OUTPUT_DIR\release\<agent>\omnispec-${Version}\"
        } else {
            Write-Error "AI-IDE 版本后置处理失败"
        }
        Write-Host ""
    } else {
        Write-Info "基础输出目录: $BASE_OUTPUT_DIR"
        Write-Info "完整路径: $BASE_OUTPUT_DIR\release\<agent>"
    }
    Write-Host ""
}

# 执行主函数
Main -Arguments $args


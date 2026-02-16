#!/usr/bin/env pwsh
# Common PowerShell functions analogous to common.sh

function Get-RepoRoot {
    try {
        $result = git rev-parse --show-toplevel 2>$null
        if ($LASTEXITCODE -eq 0) {
            return $result
        }
    } catch {
        # Git command failed
    }
    
    # Fall back to script location for non-git repos
    return (Resolve-Path (Join-Path $PSScriptRoot "../../..")).Path
}

function Get-CurrentBranch {
    # First check if SPECIFY_FEATURE environment variable is set
    if ($env:SPECIFY_FEATURE) {
        return $env:SPECIFY_FEATURE
    }
    
    # Then check git if available
    try {
        $result = git rev-parse --abbrev-ref HEAD 2>$null
        if ($LASTEXITCODE -eq 0) {
            return $result
        }
    } catch {
        # Git command failed
    }
    
    # For non-git repos, try to find the latest feature directory
    $repoRoot = Get-RepoRoot
    $changesDir = Join-Path $repoRoot "changes"
    
    if (Test-Path $changesDir) {
        $latestFeature = ""
        $highest = 0
        
        Get-ChildItem -Path $changesDir -Directory | ForEach-Object {
            if ($_.Name -match '^(\d{3})-') {
                $num = [int]$matches[1]
                if ($num -gt $highest) {
                    $highest = $num
                    $latestFeature = $_.Name
                }
            }
        }
        
        if ($latestFeature) {
            return $latestFeature
        }
    }
    
    # Final fallback
    return "main"
}

function Test-HasGit {
    try {
        git rev-parse --show-toplevel 2>$null | Out-Null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

function Test-FeatureBranch {
    param(
        [string]$Branch,
        [bool]$HasGit = $true
    )
    
    # For non-git repos, we can't enforce branch naming but still provide output
    if (-not $HasGit) {
        Write-Warning "[specify] Warning: Git repository not detected; skipped branch validation"
        return $true
    }
    
    if ($Branch -notmatch '^[0-9]{3}-') {
        Write-Output "ERROR: Not on a feature branch. Current branch: $Branch"
        Write-Output "Feature branches should be named like: 001-feature-name"
        return $false
    }
    return $true
}

function Get-FeatureDir {
    param([string]$RepoRoot, [string]$Branch)
    Join-Path $RepoRoot "changes/$Branch"
}

function Get-FeaturePathsEnv {
    $repoRoot = Get-RepoRoot
    $currentBranch = Get-CurrentBranch
    $hasGit = Test-HasGit
    $featureDir = Get-FeatureDir -RepoRoot $repoRoot -Branch $currentBranch
    
    [PSCustomObject]@{
        REPO_ROOT     = $repoRoot
        CURRENT_BRANCH = $currentBranch
        HAS_GIT       = $hasGit
        FEATURE_DIR   = $featureDir
        FEATURE_SPEC  = Join-Path $featureDir 'spec.md'
        IMPL_DESIGN   = Join-Path $featureDir 'design.md'
        TASKS         = Join-Path $featureDir 'tasks.md'
        RESEARCH      = Join-Path $featureDir 'research.md'
        DATA_MODEL    = Join-Path $featureDir 'data-model.md'
        QUICKSTART    = Join-Path $featureDir 'quickstart.md'
        CONTRACTS_DIR = Join-Path $featureDir 'contracts'
    }
}

function Test-FileExists {
    param([string]$Path, [string]$Description)
    if (Test-Path -Path $Path -PathType Leaf) {
        Write-Output "  ✓ $Description"
        return $true
    } else {
        Write-Output "  ✗ $Description"
        return $false
    }
}

function Test-DirHasFiles {
    param([string]$Path, [string]$Description)
    if ((Test-Path -Path $Path -PathType Container) -and (Get-ChildItem -Path $Path -ErrorAction SilentlyContinue | Where-Object { -not $_.PSIsContainer } | Select-Object -First 1)) {
        Write-Output "  ✓ $Description"
        return $true
    } else {
        Write-Output "  ✗ $Description"
        return $false
    }
}

# 规范化路径（转换为绝对路径）
# 参数:
#   [string]$Path: 要规范化的路径（相对路径、绝对路径或 ~ 开头的路径）
#   [string]$BasePath: 基准路径（用于相对路径转换，默认为 REPO_ROOT）
# 返回:
#   返回规范化后的绝对路径
function Normalize-Path {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Path,
        [string]$BasePath = ""
    )
    
    # 处理空路径
    if ([string]::IsNullOrEmpty($Path)) {
        return $null
    }
    
    # 如果 BasePath 为空，使用 REPO_ROOT
    if ([string]::IsNullOrEmpty($BasePath)) {
        $BasePath = Get-RepoRoot
    }
    
    # 展开 ~ 为用户主目录
    if ($Path.StartsWith("~")) {
        $Path = $Path -replace "^~", $env:HOME
    }
    
    # 如果是绝对路径，使用 Resolve-Path 或手动处理
    if ([System.IO.Path]::IsPathRooted($Path)) {
        try {
            # 使用 Resolve-Path 规范化绝对路径（如果路径存在）
            if (Test-Path -Path $Path -ErrorAction SilentlyContinue) {
                return (Resolve-Path -Path $Path -ErrorAction Stop).Path
            } else {
                # 路径不存在时，手动处理 .. 和 .
                $normalized = [System.IO.Path]::GetFullPath($Path)
                return $normalized
            }
        } catch {
            # 如果 Resolve-Path 失败，使用 GetFullPath
            try {
                return [System.IO.Path]::GetFullPath($Path)
            } catch {
                return $Path
            }
        }
    }
    
    # 处理相对路径（基于基准路径）
    $fullPath = Join-Path -Path $BasePath -ChildPath $Path
    
    # 规范化路径
    try {
        if (Test-Path -Path $fullPath -ErrorAction SilentlyContinue) {
            return (Resolve-Path -Path $fullPath -ErrorAction Stop).Path
        } else {
            # 路径不存在时，使用 GetFullPath
            return [System.IO.Path]::GetFullPath($fullPath)
        }
    } catch {
        # 如果失败，使用 GetFullPath
        try {
            return [System.IO.Path]::GetFullPath($fullPath)
        } catch {
            return $fullPath
        }
    }
}

# 获取输出目录
# 参数:
#   [string]$UserOutputDir: 用户指定的输出目录（可选）
#   [string]$ElementOutputDir: 要素类型的输出子目录（如 reverse/interfaces）
#   [string]$CurrentBranch: 当前分支名（用于判断是否在特性分支下）
#   [string]$FeatureDir: FEATURE_DIR（特性目录，如果存在）
#   [string]$RepoRoot: REPO_ROOT（仓库根目录）
# 返回:
#   返回规范化后的绝对路径（如果目录不存在会自动创建）
function Get-OutputDir {
    param(
        [string]$UserOutputDir = "",
        [Parameter(Mandatory=$true)]
        [string]$ElementOutputDir,
        [string]$CurrentBranch = "",
        [string]$FeatureDir = "",
        [Parameter(Mandatory=$true)]
        [string]$RepoRoot
    )
    
    # 如果用户指定了输出目录，优先使用（转换为绝对路径）
    if (-not [string]::IsNullOrEmpty($UserOutputDir)) {
        $outputDir = Normalize-Path -Path $UserOutputDir -BasePath $RepoRoot
        # 自动创建目录（如果不存在）
        if (-not (Test-Path -Path $outputDir -PathType Container)) {
            New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
        }
        return $outputDir
    }
    
    # 构建默认输出目录
    $outputDir = ""
    
    # 判断是否在特性分支下（分支名匹配 ^\d{3}- 模式）
    $isFeatureBranch = $false
    if (-not [string]::IsNullOrEmpty($CurrentBranch)) {
        $isFeatureBranch = $CurrentBranch -match '^\d{3}-'
    }
    
    if ($isFeatureBranch -and -not [string]::IsNullOrEmpty($FeatureDir)) {
        # 特性分支：输出到特性目录
        $outputDir = Join-Path -Path $FeatureDir -ChildPath $ElementOutputDir
    } else {
        # 非特性分支：输出到omni-doc目录
        $outputDir = Join-Path -Path $RepoRoot -ChildPath "omni-doc/$ElementOutputDir"
    }
    
    # 规范化路径
    $outputDir = Normalize-Path -Path $outputDir -BasePath $RepoRoot
    
    # 自动创建目录（如果不存在）
    if (-not (Test-Path -Path $outputDir -PathType Container)) {
        New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
    }
    
    return $outputDir
}

# 等待批次完成（带超时和轮询）
# 参数:
#   [string]$RepoRoot: 仓库根目录路径
#   [string]$BatchNumbersJson: 批次编号数组的JSON字符串，格式为 [1, 2, 3]
#   [string]$StageType: 阶段类型（scenarios/interfaces/functions/call-chain/function-identification）
#   [int]$MaxWaitMinutes: 最大等待时间（分钟，默认30）
#   [int]$CheckIntervalSeconds: 检查间隔（秒，默认30）
# 返回:
#   0: 所有批次完成
#   1: 超时或部分批次未完成
function Wait-ForBatchesCompletion {
    param(
        [Parameter(Mandatory=$true)]
        [string]$RepoRoot,
        [Parameter(Mandatory=$true)]
        [string]$BatchNumbersJson,
        [Parameter(Mandatory=$true)]
        [string]$StageType,
        [int]$MaxWaitMinutes = 30,
        [int]$CheckIntervalSeconds = 30
    )

    # 验证参数
    if ([string]::IsNullOrEmpty($RepoRoot) -or [string]::IsNullOrEmpty($BatchNumbersJson) -or [string]::IsNullOrEmpty($StageType)) {
        Write-Error "错误: Wait-ForBatchesCompletion 需要 RepoRoot, BatchNumbersJson 和 StageType 参数"
        return 1
    }

    # 获取脚本目录
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $verifyScript = Join-Path $scriptDir "verify-batches-completion.ps1"

    if (-not (Test-Path -Path $verifyScript -PathType Leaf)) {
        Write-Error "错误: 批次验证脚本不存在: $verifyScript"
        return 1
    }

    # 计算最大等待秒数
    $maxWaitSeconds = $MaxWaitMinutes * 60
    $elapsedSeconds = 0
    $iteration = 0

    Write-Host "开始等待批次完成，最多等待 $MaxWaitMinutes 分钟，每 $CheckIntervalSeconds 秒检查一次..."

    while ($elapsedSeconds -lt $maxWaitSeconds) {
        $iteration++

        # 调用验证脚本
        try {
            $verifyResult = & $verifyScript -RepoRoot $RepoRoot -BatchNumbers $BatchNumbersJson -StageType $StageType 2>&1
            $verifyOutput = $verifyResult | Out-String
            $verifyJson = $verifyOutput | ConvertFrom-Json

            if ($verifyJson.all_completed) {
                # 所有批次完成
                $completedCount = $verifyJson.completed_count
                $totalCount = $verifyJson.total_count
                Write-Host "所有批次已完成！($completedCount/$totalCount)"
                return 0
            } else {
                # 部分批次未完成
                $completedCount = $verifyJson.completed_count
                $totalCount = $verifyJson.total_count
                $remaining = $totalCount - $completedCount

                if ($iteration -eq 1 -or ($iteration % 2) -eq 0) {
                    Write-Host "等待中... 已完成 $completedCount/$totalCount 个批次，剩余 $remaining 个批次..."
                }
            }
        } catch {
            # 验证失败，继续等待
            if ($iteration -eq 1 -or ($iteration % 2) -eq 0) {
                Write-Host "等待中... 验证批次状态时出错，继续等待..."
            }
        }

        # 等待指定间隔
        Start-Sleep -Seconds $CheckIntervalSeconds
        $elapsedSeconds += $CheckIntervalSeconds
    }

    # 超时
    Write-Error "错误: 等待批次完成超时（$MaxWaitMinutes 分钟）"

    # 输出最终状态
    try {
        $finalResult = & $verifyScript -RepoRoot $RepoRoot -BatchNumbers $BatchNumbersJson -StageType $StageType 2>&1
        $finalOutput = $finalResult | Out-String
        Write-Host $finalOutput
    } catch {
        # 忽略错误
    }

    return 1
}

# 获取项目名称
# 参数:
#   [string]$RepoRoot: 仓库根目录路径
# 返回:
#   项目名称，如果未配置则返回空字符串
function Get-ProjectName {
    param(
        [Parameter(Mandatory=$true)]
        [string]$RepoRoot
    )
    
    # 1. 从环境变量读取（优先级最高）
    if ($env:OMNISPEC_PROJECT_NAME) {
        return $env:OMNISPEC_PROJECT_NAME
    }
    
    # 2. 从配置文件读取
    $configFile = Join-Path $RepoRoot ".specify/config.yaml"
    if (Test-Path -Path $configFile -PathType Leaf) {
        try {
            # 尝试从 YAML 文件中提取 project_name
            if (Get-Command yq -ErrorAction SilentlyContinue) {
                $projectName = yq -r '.project_name // empty' $configFile 2>$null
                if ($projectName) {
                    return $projectName
                }
            } elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
                $projectName = python3 -c "import yaml, sys; data = yaml.safe_load(open('$configFile')); print(data.get('project_name', '') if data else '')" 2>$null
                if ($projectName) {
                    return $projectName
                }
            } else {
                # 简单的正则提取
                $content = Get-Content $configFile -Raw
                if ($content -match 'project_name\s*:\s*["'']?([^"'']+)["'']?') {
                    return $matches[1]
                }
            }
        } catch {
            # 忽略错误
        }
    }
    
    # 3. 从简单的文本文件读取
    $projectNameFile = Join-Path $RepoRoot ".specify/project-name"
    if (Test-Path -Path $projectNameFile -PathType Leaf) {
        $projectName = (Get-Content $projectNameFile -First 1 -ErrorAction SilentlyContinue).Trim()
        if ($projectName) {
            return $projectName
        }
    }
    
    # 未找到项目名称
    return $null
}

# 查找模板文件（支持按项目查找）
# 参数:
#   [string]$TemplateFilename: 模板文件名（如 reverse-interface-detail-template.md）
#   [string]$RepoRoot: 仓库根目录路径
#   [string]$UserTemplate: 用户指定的模板路径（可选）
#   [string]$OmniSpecRoot: OmniSpec 根目录路径（可选，用于查找系统默认模板）
# 返回:
#   返回模板文件的绝对路径，如果未找到则返回 $null
function Find-TemplateFile {
    param(
        [Parameter(Mandatory=$true)]
        [string]$TemplateFilename,
        [Parameter(Mandatory=$true)]
        [string]$RepoRoot,
        [string]$UserTemplate = "",
        [string]$OmniSpecRoot = ""
    )
    
    $searchedPaths = @()
    
    # 1. 用户指定的模板（优先级最高）
    if (-not [string]::IsNullOrEmpty($UserTemplate)) {
        $absTemplate = Normalize-Path -Path $UserTemplate -BasePath $RepoRoot
        $searchedPaths += $absTemplate
        if (Test-Path -Path $absTemplate -PathType Leaf) {
            return $absTemplate
        }
    }
    
    # 2. 项目特定模板（如果配置了项目名称）
    $projectName = Get-ProjectName -RepoRoot $RepoRoot
    if ($projectName) {
        $projectTemplate = Join-Path $RepoRoot ".specify/templates/$projectName/$TemplateFilename"
        $searchedPaths += $projectTemplate
        if (Test-Path -Path $projectTemplate -PathType Leaf) {
            return $projectTemplate
        }
    }
    
    # 3. 项目根目录下的默认模板（向后兼容）
    $projectDefaultTemplate = Join-Path $RepoRoot ".specify/templates/$TemplateFilename"
    $searchedPaths += $projectDefaultTemplate
    if (Test-Path -Path $projectDefaultTemplate -PathType Leaf) {
        return $projectDefaultTemplate
    }
    
    # 4. 项目根目录下的 default 子目录模板
    $projectDefaultDirTemplate = Join-Path $RepoRoot ".specify/templates/default/$TemplateFilename"
    $searchedPaths += $projectDefaultDirTemplate
    if (Test-Path -Path $projectDefaultDirTemplate -PathType Leaf) {
        return $projectDefaultDirTemplate
    }
    
    # 5. 系统默认模板（OmniSpec 根目录）
    if (-not [string]::IsNullOrEmpty($OmniSpecRoot)) {
        $systemDefaultTemplate = Join-Path $OmniSpecRoot "specify/templates/default/$TemplateFilename"
        $searchedPaths += $systemDefaultTemplate
        if (Test-Path -Path $systemDefaultTemplate -PathType Leaf) {
            return $systemDefaultTemplate
        }
        
        # 向后兼容：系统根目录下的模板
        $systemTemplate = Join-Path $OmniSpecRoot "specify/templates/$TemplateFilename"
        $searchedPaths += $systemTemplate
        if (Test-Path -Path $systemTemplate -PathType Leaf) {
            return $systemTemplate
        }
    }
    
    # 所有模板都找不到，报错
    Write-Error "错误: 模板文件未找到: $TemplateFilename"
    Write-Error "已查找的路径："
    foreach ($path in $searchedPaths) {
        Write-Error "  - $path"
    }
    return $null
}

# 判断是否需要用户确认
# 参数: 从 $env:ARGUMENTS 环境变量或命令行参数中读取
# 返回: $true 需要确认, $false 不需要确认
function Test-ShouldRequireConfirmation {
    param([string]$Args = "")
    
    if ([string]::IsNullOrEmpty($Args)) {
        $Args = $env:ARGUMENTS
    }
    
    # 如果指定了 --non-interactive 或 --yes，不需要确认
    if ($Args -match '--non-interactive' -or $Args -match '--yes') {
        return $false
    }
    
    # 解析 --interactive yes/no 格式
    # 支持格式：--interactive yes、--interactive no、--interactive（默认yes）
    if ($Args -match '--interactive\s+no') {
        # --interactive no 明确禁用交互模式
        return $false
    } elseif ($Args -match '--interactive\s+yes' -or $Args -match '--interactive(\s|$)') {
        # --interactive yes 或 --interactive（无参数，默认yes）启用交互模式
        return $true
    }
    
    # 默认：不需要确认（全自动模式）
    return $false
}


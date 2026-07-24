#!/usr/bin/env pwsh

# reverse - 从代码库中反构各种类型的要素，生成标准化的要素文档
#
# 第一阶段支持接口清单（interfaces）反构
#
# Usage: reverse.ps1 [OPTIONS]
#
# 详细用法请参考 -Help

$ErrorActionPreference = 'Stop'

# 脚本目录
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# 加载公共函数
. (Join-Path $ScriptDir "common.ps1")

# 加载要素类型注册表
. (Join-Path $ScriptDir "reverse/element-registry.ps1")

# 加载接口辅助函数模块（按需加载）
# 注意：接口辅助函数模块包含所有接口相关的函数，方便后续扩展其他要素类型
# 如果使用了接口相关的辅助命令，则加载模块
$script:INTERFACE_HELPERS_LOADED = $false
if ($args.Count -gt 0) {
    switch ($args[0]) {
        { $_ -in @('--load-few-shot-template', '--extract-identification-rules', '--extract-constraints', '--extract-format-definition', '--extract-interface-types', '--format-rules-for-prompt') } {
            # 辅助命令，需要加载接口辅助函数模块
            $interfaceHelpersModule = Join-Path $ScriptDir "reverse/interfaces/utils/interface-helpers.ps1"
            if (Test-Path -Path $interfaceHelpersModule) {
                . $interfaceHelpersModule
                $script:INTERFACE_HELPERS_LOADED = $true
            } else {
                Write-LogError "接口辅助函数模块不存在: $interfaceHelpersModule"
                exit $SCRIPT:ERROR_INVALID_PARAMS
            }
            break
        }
    }
}

# 获取仓库根目录
$REPO_ROOT = Get-RepoRoot

# 错误码定义（参考设计文档 8.4 节，与 Bash 版本一致）
# 参数和配置错误 (1-10)
$SCRIPT:ERROR_INVALID_PARAMS = 1
$SCRIPT:ERROR_INVALID_TARGET = 2
$SCRIPT:ERROR_INVALID_INTERFACE_TYPES = 3
$SCRIPT:ERROR_MISSING_REQUIRED_PARAM = 4
$SCRIPT:ERROR_INVALID_PARAM_COMBINATION = 5
$SCRIPT:ERROR_PERMISSION_DENIED = 6
$SCRIPT:ERROR_DISK_FULL = 7
$SCRIPT:ERROR_DEPENDENCY_MISSING = 8
$SCRIPT:ERROR_CACHE_ERROR = 9
$SCRIPT:ERROR_MERGE_CONFLICT = 10

# 文件系统错误 (11-20)
$SCRIPT:ERROR_FILE_NOT_FOUND = 11
$SCRIPT:ERROR_FILE_READ_ERROR = 12
$SCRIPT:ERROR_FILE_WRITE_ERROR = 13
$SCRIPT:ERROR_PERMISSION_DENIED_FS = 14
$SCRIPT:ERROR_DISK_FULL_FS = 15
$SCRIPT:ERROR_DIRECTORY_NOT_FOUND = 16

# 分析处理错误 (21-30)
$SCRIPT:ERROR_ANALYSIS_FAILED = 21
$SCRIPT:ERROR_DEPENDENCY_MISSING_ANALYSIS = 22
$SCRIPT:ERROR_LANGUAGE_NOT_SUPPORTED = 23

# 输出和模板错误 (31-40)
$SCRIPT:ERROR_TEMPLATE_ERROR = 31
$SCRIPT:ERROR_TEMPLATE_NOT_FOUND = 32
$SCRIPT:ERROR_OUTPUT_FAILED = 33
$SCRIPT:ERROR_JSON_OUTPUT_FAILED = 34

# 缓存和合并错误 (41-50)
$SCRIPT:ERROR_CACHE_ERROR_MERGE = 41
$SCRIPT:ERROR_MERGE_CONFLICT_DETAIL = 42
$SCRIPT:ERROR_MERGE_FAILED = 43

# 日志函数
function Write-LogInfo {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Cyan
}

function Write-LogWarn {
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Write-LogError {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Write-LogDebug {
    param([string]$Message)
    if ($script:VERBOSE) {
        Write-Host "[DEBUG] $Message" -ForegroundColor Gray
    }
}

function Write-LogSuccess {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

# 检测是否为交互式终端
# 返回:
#   $true: 是交互式终端
#   $false: 不是交互式终端
function Test-IsInteractive {
    # 在 PowerShell 中检测是否为交互式终端
    # 方法1: 检查 $Host.UI.RawUI.KeyAvailable（如果可用）
    # 方法2: 检查环境变量（CI/CD 环境通常设置 CI=true）
    # 方法3: 检查标准输入是否为终端
    
    # 检查是否在 CI/CD 环境
    if ($env:CI -eq "true" -or $env:TF_BUILD -eq "true" -or $env:JENKINS_URL) {
        return $false
    }
    
    # 检查标准输入是否为终端
    try {
        # 在 PowerShell Core (pwsh) 中，可以使用 [Console]::IsInputRedirected
        if ([Console]::IsInputRedirected) {
            return $false
        }
        
        # 尝试读取一个键（不阻塞）
        if ($Host.UI.RawUI.KeyAvailable) {
            return $true
        }
        
        # 检查是否在交互式主机中
        if ($Host.Name -eq "ConsoleHost" -or $Host.Name -eq "Windows PowerShell ISE Host") {
            return $true
        }
        
        # 默认情况下，如果在 PowerShell 交互式环境中，返回 true
        return $true
    } catch {
        # 如果检测失败，假设是交互式终端
        return $true
    }
}

# 确认交互模式
# 根据参数和环境确定是否应该使用交互模式
# 返回:
#   $true: 应该使用交互模式
#   $false: 不应该使用交互模式
function Test-ShouldUseInteractive {
    # 如果指定了 --non-interactive，强制非交互模式
    if ($script:NON_INTERACTIVE -eq $true) {
        return $false
    }
    
    # 如果指定了 --yes，自动接受所有默认选项，非交互模式
    if ($script:YES -eq $true) {
        return $false
    }
    
    # 如果指定了 --interactive，强制交互模式
    if ($script:INTERACTIVE -eq $true) {
        # 检查是否在交互式终端
        if (Test-IsInteractive) {
            return $true
        } else {
            Write-LogError "错误: --interactive 参数已指定，但当前不在交互式终端"
            Write-LogError "提示: 在非交互式终端中，请使用 --non-interactive 或 --yes 参数"
            exit $script:ERROR_INVALID_PARAM_COMBINATION
        }
    }
    
    # 默认情况下，如果在交互式终端，使用交互模式
    if (Test-IsInteractive) {
        return $true
    } else {
        return $false
    }
}

# 提示用户确认（带默认选项）
# 参数:
#   $Prompt: 提示信息
#   $Default: 默认选项（Y 或 n，默认为 Y）
# 返回:
#   $true: 用户选择 Yes
#   $false: 用户选择 No
# 注意: 在非交互模式下，如果默认选项是 Y，返回 $true；如果是 n，返回 $false
function Request-Confirm {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Prompt,
        
        [Parameter(Mandatory=$false)]
        [string]$Default = "Y"
    )
    
    # 如果不在交互模式，使用默认选项
    if (-not (Test-ShouldUseInteractive)) {
        if ($Default -eq "Y" -or $Default -eq "y") {
            return $true
        } else {
            return $false
        }
    }
    
    # 构建提示信息（包含默认选项）
    $promptWithDefault = if ($Default -eq "Y" -or $Default -eq "y") {
        "$Prompt [Y/n]: "
    } else {
        "$Prompt [y/N]: "
    }
    
    # 读取用户输入
    while ($true) {
        $response = Read-Host $promptWithDefault
        
        # 如果用户直接按回车，使用默认选项
        if ([string]::IsNullOrEmpty($response)) {
            if ($Default -eq "Y" -or $Default -eq "y") {
                return $true
            } else {
                return $false
            }
        }
        
        # 处理用户输入（不区分大小写）
        $responseLower = $response.ToLower()
        switch ($responseLower) {
            { $_ -eq "y" -or $_ -eq "yes" } {
                return $true
            }
            { $_ -eq "n" -or $_ -eq "no" } {
                return $false
            }
            default {
                Write-LogWarn "无效输入，请输入 Y 或 n"
            }
        }
    }
}

# 显示帮助信息
function Show-Help {
    Write-Output @"
reverse - 从代码库中反构各种类型的要素，生成标准化的要素文档

用法：
  reverse.ps1 [OPTIONS]

必需参数：
  --target <type>           目标要素类型（第一阶段支持 'interfaces'）

可选参数：
范围指定：
  --path <path1,path2,...>  反构的目录路径（逗号分隔）
  --files <file1,file2,...> 反构的文件路径（逗号分隔）
                           注意：--path 和 --files 至少需要指定一个

接口类型过滤（仅当 --target interfaces 时使用）：
  --interface-types <types> 指定要反构的接口类型（逗号分隔）
                           支持的类型：restful, message, module, cli, rpc, function, other

输出控制：
  --output-dir <dir>        输出目录，默认根据分支类型决定
  --template <file>         模板文件路径，默认使用内置模板
  --preview                 预览模式，不写入文件
  --json                    JSON 格式输出

交互模式：
  --interactive             启用交互式确认
  --non-interactive         强制非交互模式
  --yes                     非交互模式，自动接受所有默认选项

增量反构：
  --incremental             增量反构模式
  --git-diff <commit>       基于 Git 提交差异反构（需配合 --incremental）
  --since <date>            基于时间戳反构（需配合 --incremental）
  --merge                   合并到现有清单文件（需配合 --incremental）

其他选项：
  --validate                启用结果校验
  --exclude <pattern>       排除文件模式（可多次使用）
  --clear-cache             清理缓存
  --verbose                 详细输出模式
  --help, -h                显示此帮助信息

参数说明：
  --target                  目标要素类型，第一阶段支持 'interfaces'
  --path, --files           至少需要指定一个，可以同时使用（取并集）
  --interface-types         仅当 --target interfaces 时使用，默认反构所有类型
  --incremental             需要配合 --git-diff 或 --since 使用
  --merge                   需要配合 --incremental 使用
  --git-diff, --since       需要配合 --incremental 使用，且不能同时指定
  --interactive             与 --non-interactive/--yes 互斥

使用示例：
  # 反构整个代码库的接口
  .\reverse.ps1 --target interfaces --path .

  # 反构指定目录的接口
  .\reverse.ps1 --target interfaces --path src/api/,src/services/

  # 仅反构 RESTful 和消息类接口
  .\reverse.ps1 --target interfaces --path src/ --interface-types restful,message

  # 反构指定文件的接口
  .\reverse.ps1 --target interfaces --files src/api/user.py

  # 交互式反构
  .\reverse.ps1 --target interfaces --path src/ --interactive

  # 预览模式
  .\reverse.ps1 --target interfaces --path src/ --preview

  # JSON 输出
  .\reverse.ps1 --target interfaces --path src/ --json

  # 增量反构
  .\reverse.ps1 --target interfaces --incremental --git-diff HEAD~1 --merge

更多信息：
  请参考设计文档：omni-infra/design/omni_reverse_interface_inventory_design.md

"@
}

# 参数解析函数（第一阶段：基础框架）
function Parse-Args {
    param([string[]]$Arguments)
    
    # 初始化参数变量
    $script:TARGET = ""
    $script:PATHS = ""
    $script:FILES = ""
    $script:INTERFACE_TYPES = ""
    $script:OUTPUT_DIR = ""
    $script:TEMPLATE = ""
    $script:INTERACTIVE = $false
    $script:NON_INTERACTIVE = $false
    $script:YES = $false
    $script:PREVIEW = $false
    $script:INCREMENTAL = $false
    $script:GIT_DIFF = ""
    $script:SINCE = ""
    $script:MERGE = $false
    $script:VALIDATE = $false
    $script:EXCLUDE_PATTERNS = @()
    $script:CLEAR_CACHE = $false
    $script:VERBOSE = $false
    $script:JSON = $false
    $script:HELP = $false

    # 参数解析循环
    $i = 0
    while ($i -lt $Arguments.Count) {
        $arg = $Arguments[$i]
        switch ($arg) {
            '--target' {
                if ($i + 1 -ge $Arguments.Count) {
                    Write-LogError "参数错误: --target 需要指定值"
                    exit $SCRIPT:ERROR_INVALID_PARAMS
                }
                $script:TARGET = $Arguments[$i + 1]
                $i += 2
            }
            '--path' {
                if ($i + 1 -ge $Arguments.Count) {
                    Write-LogError "参数错误: --path 需要指定值"
                    exit $SCRIPT:ERROR_INVALID_PARAMS
                }
                $script:PATHS = $Arguments[$i + 1]
                $i += 2
            }
            '--files' {
                if ($i + 1 -ge $Arguments.Count) {
                    Write-LogError "参数错误: --files 需要指定值"
                    exit $SCRIPT:ERROR_INVALID_PARAMS
                }
                $script:FILES = $Arguments[$i + 1]
                $i += 2
            }
            '--interface-types' {
                if ($i + 1 -ge $Arguments.Count) {
                    Write-LogError "参数错误: --interface-types 需要指定值"
                    exit $SCRIPT:ERROR_INVALID_PARAMS
                }
                $script:INTERFACE_TYPES = $Arguments[$i + 1]
                $i += 2
            }
            '--output-dir' {
                if ($i + 1 -ge $Arguments.Count) {
                    Write-LogError "参数错误: --output-dir 需要指定值"
                    exit $SCRIPT:ERROR_INVALID_PARAMS
                }
                $script:OUTPUT_DIR = $Arguments[$i + 1]
                $i += 2
            }
            '--template' {
                if ($i + 1 -ge $Arguments.Count) {
                    Write-LogError "参数错误: --template 需要指定值"
                    exit $SCRIPT:ERROR_INVALID_PARAMS
                }
                $script:TEMPLATE = $Arguments[$i + 1]
                $i += 2
            }
            '--interactive' {
                $script:INTERACTIVE = $true
                $i++
            }
            '--non-interactive' {
                $script:NON_INTERACTIVE = $true
                $i++
            }
            '--yes' {
                $script:YES = $true
                $i++
            }
            '--preview' {
                $script:PREVIEW = $true
                $i++
            }
            '--incremental' {
                $script:INCREMENTAL = $true
                $i++
            }
            '--git-diff' {
                if ($i + 1 -ge $Arguments.Count) {
                    Write-LogError "参数错误: --git-diff 需要指定值"
                    exit $SCRIPT:ERROR_INVALID_PARAMS
                }
                $script:GIT_DIFF = $Arguments[$i + 1]
                $i += 2
            }
            '--since' {
                if ($i + 1 -ge $Arguments.Count) {
                    Write-LogError "参数错误: --since 需要指定值"
                    exit $SCRIPT:ERROR_INVALID_PARAMS
                }
                $script:SINCE = $Arguments[$i + 1]
                $i += 2
            }
            '--merge' {
                $script:MERGE = $true
                $i++
            }
            '--validate' {
                $script:VALIDATE = $true
                $i++
            }
            '--exclude' {
                if ($i + 1 -ge $Arguments.Count) {
                    Write-LogError "参数错误: --exclude 需要指定值"
                    exit $SCRIPT:ERROR_INVALID_PARAMS
                }
                $script:EXCLUDE_PATTERNS += $Arguments[$i + 1]
                $i += 2
            }
            '--clear-cache' {
                $script:CLEAR_CACHE = $true
                $i++
            }
            '--verbose' {
                $script:VERBOSE = $true
                $i++
            }
            '--json' {
                $script:JSON = $true
                $i++
            }
            '--help' {
                $script:HELP = $true
                $i++
            }
            '-h' {
                $script:HELP = $true
                $i++
            }
            default {
                Write-LogError "未知参数: $arg"
                Write-LogError "使用 --help 查看帮助信息"
                exit $SCRIPT:ERROR_INVALID_PARAMS
            }
        }
    }

    Write-LogDebug "参数解析完成"
}

# 参数验证函数（第一阶段：基础验证框架）
function Test-Params {
    # 显示帮助信息
    if ($script:HELP) {
        Show-Help
        exit 0
    }

    # 检查必需参数
    if ([string]::IsNullOrEmpty($script:TARGET)) {
        Write-LogError "参数错误: --target 必须指定"
        Write-LogError "使用 --help 查看帮助信息"
        exit $SCRIPT:ERROR_MISSING_REQUIRED_PARAM
    }

    # 检查范围参数（--path 和 --files 至少指定一个）
    if ([string]::IsNullOrEmpty($script:PATHS) -and [string]::IsNullOrEmpty($script:FILES)) {
        Write-LogError "参数错误: --path 和 --files 至少需要指定一个"
        Write-LogError "使用 --help 查看帮助信息"
        exit $SCRIPT:ERROR_MISSING_REQUIRED_PARAM
    }

    # 检查参数组合（交互模式）
    if ($script:INTERACTIVE -and $script:NON_INTERACTIVE) {
        Write-LogError "参数错误: --interactive 和 --non-interactive 不能同时使用"
        exit $SCRIPT:ERROR_INVALID_PARAM_COMBINATION
    }

    if ($script:INTERACTIVE -and $script:YES) {
        Write-LogError "参数错误: --interactive 和 --yes 不能同时使用"
        exit $SCRIPT:ERROR_INVALID_PARAM_COMBINATION
    }

    # 检查参数组合（增量反构）
    # 先检查互斥参数
    if (-not [string]::IsNullOrEmpty($script:GIT_DIFF) -and -not [string]::IsNullOrEmpty($script:SINCE)) {
        Write-LogError "参数错误: --git-diff 和 --since 不能同时指定"
        exit $SCRIPT:ERROR_INVALID_PARAM_COMBINATION
    }

    # 再检查依赖关系
    if ($script:MERGE -and -not $script:INCREMENTAL) {
        Write-LogError "参数错误: --merge 需要配合 --incremental 使用"
        exit $SCRIPT:ERROR_INVALID_PARAM_COMBINATION
    }

    if (-not [string]::IsNullOrEmpty($script:GIT_DIFF) -and -not $script:INCREMENTAL) {
        Write-LogError "参数错误: --git-diff 需要配合 --incremental 使用"
        exit $SCRIPT:ERROR_INVALID_PARAM_COMBINATION
    }

    if (-not [string]::IsNullOrEmpty($script:SINCE) -and -not $script:INCREMENTAL) {
        Write-LogError "参数错误: --since 需要配合 --incremental 使用"
        exit $SCRIPT:ERROR_INVALID_PARAM_COMBINATION
    }

    # 验证 --target 是否是有效值（从注册表查找）
    if (-not (Test-ValidElementType -Target $script:TARGET)) {
        $validTypes = Get-AllElementTypes
        Write-LogError "参数错误: --target '$($script:TARGET)' 不是有效的要素类型"
        Write-LogError "支持的要素类型: $($validTypes -join ' ')"
        Write-LogError "使用 --help 查看帮助信息"
        exit $SCRIPT:ERROR_INVALID_TARGET
    }

    # 验证 --interface-types 是否是有效类型（仅当 --target interfaces 时）
    if ($script:TARGET -eq "interfaces" -and -not [string]::IsNullOrEmpty($script:INTERFACE_TYPES)) {
        # 定义有效的接口类型
        $validInterfaceTypes = @("restful", "message", "module", "cli", "rpc", "function", "other")
        
        # 将逗号分隔的接口类型字符串分割为数组
        $typesArray = $script:INTERFACE_TYPES -split ',' | ForEach-Object { $_.Trim() }
        
        # 验证每个接口类型
        foreach ($interfaceType in $typesArray) {
            if ($interfaceType -notin $validInterfaceTypes) {
                Write-LogError "参数错误: --interface-types 包含无效类型: '$interfaceType'"
                Write-LogError "支持的接口类型: $($validInterfaceTypes -join ' ')"
                Write-LogError "使用 --help 查看帮助信息"
                exit $SCRIPT:ERROR_INVALID_INTERFACE_TYPES
            }
        }
    }

    # 验证路径和文件是否存在
    if (-not [string]::IsNullOrEmpty($script:PATHS)) {
        # 将逗号分隔的路径字符串分割为数组
        $pathsArray = $script:PATHS -split ',' | ForEach-Object { $_.Trim() }
        
        foreach ($path in $pathsArray) {
            # 将相对路径转换为绝对路径（基于 REPO_ROOT）
            $absPath = Normalize-Path -Path $path -BasePath $REPO_ROOT
            if ($null -eq $absPath) {
                Write-LogError "参数错误: 无法规范化路径: $path"
                exit $SCRIPT:ERROR_INVALID_PARAMS
            }
            
            # 检查路径是否存在
            if (-not (Test-Path -LiteralPath $absPath)) {
                Write-LogError "参数错误: 路径不存在: $path (解析为: $absPath)"
                Write-LogError "使用 --help 查看帮助信息"
                exit $SCRIPT:ERROR_FILE_NOT_FOUND
            }
        }
    }

    if (-not [string]::IsNullOrEmpty($script:FILES)) {
        # 将逗号分隔的文件字符串分割为数组
        $filesArray = $script:FILES -split ',' | ForEach-Object { $_.Trim() }
        
        foreach ($file in $filesArray) {
            # 将相对路径转换为绝对路径（基于 REPO_ROOT）
            $absFile = Normalize-Path -Path $file -BasePath $REPO_ROOT
            if ($null -eq $absFile) {
                Write-LogError "参数错误: 无法规范化文件路径: $file"
                exit $SCRIPT:ERROR_INVALID_PARAMS
            }
            
            # 检查文件是否存在
            if (-not (Test-Path -LiteralPath $absFile -PathType Leaf)) {
                Write-LogError "参数错误: 文件不存在: $file (解析为: $absFile)"
                Write-LogError "使用 --help 查看帮助信息"
                exit $SCRIPT:ERROR_FILE_NOT_FOUND
            }
        }
    }

    Write-LogDebug "参数验证完成"
}

# 检查文件是否匹配模式
# 参数:
#   [string]$FilePath: 文件路径（绝对路径）
#   [string]$Pattern: 模式（支持 glob 模式，如 **/*test*.py）
#   [string]$RepoRoot: 仓库根目录（用于将绝对路径转换为相对路径进行匹配）
# 返回:
#   匹配: 返回 $true
#   不匹配: 返回 $false
function Test-MatchesPattern {
    param(
        [Parameter(Mandatory=$true)]
        [string]$FilePath,
        [Parameter(Mandatory=$true)]
        [string]$Pattern,
        [Parameter(Mandatory=$true)]
        [string]$RepoRoot
    )
    
    # 将绝对路径转换为相对于仓库根目录的路径
    $relPath = $FilePath
    if ($FilePath.StartsWith($RepoRoot)) {
        $relPath = $FilePath.Substring($RepoRoot.Length)
        if ($relPath.StartsWith([System.IO.Path]::DirectorySeparatorChar) -or $relPath.StartsWith([System.IO.Path]::AltDirectorySeparatorChar)) {
            $relPath = $relPath.Substring(1)
        }
    }
    
    # 处理包含 ** 的模式（递归匹配）
    if ($Pattern -match '\*\*') {
        # 将 glob 模式转换为正则表达式
        $regexPattern = $Pattern
        
        # 先将 ** 替换为占位符
        $regexPattern = $regexPattern -replace '\*\*', '__STARSTAR__'
        
        # 转义特殊字符（但保留占位符）
        $regexPattern = [regex]::Escape($regexPattern)
        
        # 将 glob 元字符转换为正则表达式
        $regexPattern = $regexPattern -replace '\\\*', '[^/]*'  # * 匹配除 / 外的任意字符
        $regexPattern = $regexPattern -replace '\\\?', '[^/]'   # ? 匹配除 / 外的单个字符
        $regexPattern = $regexPattern -replace '__STARSTAR__', '.*'  # ** 匹配任意字符（包括 /）
        
        # 使用正则表达式匹配
        if ($relPath -match "^$regexPattern$") {
            return $true
        }
    } else {
        # 简单模式匹配（不含 **），使用 PowerShell 的 -like 运算符
        # PowerShell 的 -like 支持 * 和 ? 通配符
        if ($relPath -like $Pattern) {
            return $true
        }
    }
    
    return $false
}

# 文件过滤函数
# 参数:
#   [string[]]$Files: 文件列表（绝对路径数组）
#   [string[]]$ExcludePatterns: 排除模式数组
#   [string]$RepoRoot: 仓库根目录
# 返回:
#   返回过滤后的文件列表（数组）
function Filter-Files {
    param(
        [Parameter(Mandatory=$true)]
        [string[]]$Files,
        [Parameter(Mandatory=$false)]
        [string[]]$ExcludePatterns = @(),
        [Parameter(Mandatory=$true)]
        [string]$RepoRoot
    )
    
    # 默认排除规则
    $defaultExcludePatterns = @(
        "**/__pycache__/**"
        "**/node_modules/**"
        "**/target/**"
        "**/build/**"
        "**/.git/**"
    )
    
    # 检查是否是 git 仓库
    $hasGit = Test-HasGit
    
    $filteredFiles = @()
    
    foreach ($filePath in $Files) {
        if ([string]::IsNullOrEmpty($filePath)) {
            continue
        }
        
        $shouldExclude = $false
        
        # 优先级 1: 检查 .gitignore（最高优先级）
        if ($hasGit) {
            try {
                $result = git check-ignore $filePath 2>$null
                if ($LASTEXITCODE -eq 0) {
                    Write-LogDebug "文件被 .gitignore 排除: $filePath"
                    $shouldExclude = $true
                }
            } catch {
                # git check-ignore 失败，继续处理
            }
        }
        
        # 优先级 2: 检查默认排除规则
        if (-not $shouldExclude) {
            foreach ($pattern in $defaultExcludePatterns) {
                if (Test-MatchesPattern -FilePath $filePath -Pattern $pattern -RepoRoot $RepoRoot) {
                    Write-LogDebug "文件被默认排除规则排除: $filePath (模式: $pattern)"
                    $shouldExclude = $true
                    break
                }
            }
        }
        
        # 优先级 3: 检查 --exclude 参数指定的规则
        if (-not $shouldExclude) {
            foreach ($pattern in $ExcludePatterns) {
                if ([string]::IsNullOrEmpty($pattern)) {
                    continue
                }
                if (Test-MatchesPattern -FilePath $filePath -Pattern $pattern -RepoRoot $RepoRoot) {
                    Write-LogDebug "文件被 --exclude 规则排除: $filePath (模式: $pattern)"
                    $shouldExclude = $true
                    break
                }
            }
        }
        
        # 如果文件未被排除，添加到结果列表
        if (-not $shouldExclude) {
            $filteredFiles += $filePath
        }
    }
    
    return $filteredFiles
}

# 范围解析函数
# 参数:
#   [string]$PathsStr: PATHS 字符串（逗号分隔的路径列表）
#   [string]$FilesStr: FILES 字符串（逗号分隔的文件列表）
#   [string]$RepoRoot: 仓库根目录
# 返回:
#   通过全局变量设置：
#   - $script:RESOLVED_PATHS: 数组，包含所有规范化的路径（绝对路径）
#   - $script:RESOLVED_FILES: 数组，包含所有规范化的文件路径（绝对路径）
#   函数返回 $true 表示成功，$false 表示失败
function Resolve-Scope {
    param(
        [string]$PathsStr = "",
        [string]$FilesStr = "",
        [Parameter(Mandatory=$true)]
        [string]$RepoRoot
    )
    
    # 初始化结果数组
    $script:RESOLVED_PATHS = @()
    $script:RESOLVED_FILES = @()
    
    # 处理 --path 参数
    if (-not [string]::IsNullOrEmpty($PathsStr)) {
        # 将逗号分隔的路径字符串分割为数组
        $pathsArray = $PathsStr -split ',' | ForEach-Object { $_.Trim() }
        
        foreach ($path in $pathsArray) {
            if ([string]::IsNullOrEmpty($path)) {
                continue
            }
            
            # 将相对路径转换为绝对路径（基于 REPO_ROOT）
            $absPath = Normalize-Path -Path $path -BasePath $RepoRoot
            if ($null -eq $absPath) {
                Write-LogError "无法规范化路径: $path"
                return $false
            }
            
            # 验证路径是否存在（在 Test-Params 中已验证，这里再次确认）
            if (-not (Test-Path -LiteralPath $absPath)) {
                Write-LogError "路径不存在: $path (解析为: $absPath)"
                return $false
            }
            
            # 添加到结果数组
            $script:RESOLVED_PATHS += $absPath
        }
    }
    
    # 处理 --files 参数
    if (-not [string]::IsNullOrEmpty($FilesStr)) {
        # 将逗号分隔的文件字符串分割为数组
        $filesArray = $FilesStr -split ',' | ForEach-Object { $_.Trim() }
        
        foreach ($file in $filesArray) {
            if ([string]::IsNullOrEmpty($file)) {
                continue
            }
            
            # 将相对路径转换为绝对路径（基于 REPO_ROOT）
            $absFile = Normalize-Path -Path $file -BasePath $RepoRoot
            if ($null -eq $absFile) {
                Write-LogError "无法规范化文件路径: $file"
                return $false
            }
            
            # 验证文件是否存在（在 Test-Params 中已验证，这里再次确认）
            if (-not (Test-Path -LiteralPath $absFile -PathType Leaf)) {
                Write-LogError "文件不存在: $file (解析为: $absFile)"
                return $false
            }
            
            # 添加到结果数组
            $script:RESOLVED_FILES += $absFile
        }
    }
    
    Write-LogDebug "范围解析完成: $($script:RESOLVED_PATHS.Count) 个路径, $($script:RESOLVED_FILES.Count) 个文件"
    return $true
}

# 要素类型分发函数
# 参数:
#   [string]$Target: 要素类型标识符
#   [string]$RepoRoot: 仓库根目录
#   [string]$ScriptDir: 脚本目录
# 返回:
#   通过全局变量设置：
#   - $script:ELEMENT_NAME: 要素类型名称（中文）
#   - $script:ELEMENT_SCANNER: 扫描函数名
#   - $script:ELEMENT_ANALYZER: 分析函数名
#   - $script:ELEMENT_VALIDATOR: 验证函数名（可能为 null）
#   - $script:ELEMENT_MERGER: 合并函数名（可能为 null）
#   - $script:ELEMENT_TEMPLATE: 模板文件名
#   - $script:ELEMENT_OUTPUT_DIR: 输出目录
#   - $script:ELEMENT_DIR: 要素类型模块目录
#   函数返回 $true 表示成功，$false 表示失败
function Invoke-ElementTypeDispatch {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Target,
        [Parameter(Mandatory=$true)]
        [string]$RepoRoot,
        [Parameter(Mandatory=$true)]
        [string]$ScriptDir
    )
    
    # 从注册表获取要素类型信息
    $elementInfo = Get-ElementTypeInfo -Target $Target
    if ($null -eq $elementInfo) {
        $validTypes = Get-AllElementTypes
        Write-LogError "不支持的要素类型: $Target"
        Write-LogError "支持的要素类型: $($validTypes -join ' ')"
        exit $SCRIPT:ERROR_INVALID_TARGET
    }
    
    # 设置全局变量
    $script:ELEMENT_NAME = $elementInfo.Name
    $script:ELEMENT_SCANNER = $elementInfo.Scanner
    $script:ELEMENT_ANALYZER = $elementInfo.Analyzer
    $script:ELEMENT_VALIDATOR = $elementInfo.Validator
    $script:ELEMENT_MERGER = $elementInfo.Merger
    $script:ELEMENT_TEMPLATE = $elementInfo.Template
    $script:ELEMENT_OUTPUT_DIR = $elementInfo.OutputDir
    $script:ELEMENT_DIR = Join-Path $ScriptDir "reverse/$Target"
    
    # 加载接口辅助函数模块（如果目标要素类型是interfaces）
    if ($Target -eq "interfaces" -and -not $script:INTERFACE_HELPERS_LOADED) {
        $interfaceHelpersModule = Join-Path $ScriptDir "reverse/interfaces/utils/interface-helpers.ps1"
        if (Test-Path -Path $interfaceHelpersModule) {
            . $interfaceHelpersModule
            $script:INTERFACE_HELPERS_LOADED = $true
            Write-LogDebug "已加载接口辅助函数模块: $interfaceHelpersModule"
        } else {
            Write-LogWarn "接口辅助函数模块不存在: $interfaceHelpersModule"
            Write-LogWarn "某些接口相关功能可能不可用"
        }
    }
    
    # 验证要素类型模块目录是否存在
    if (-not (Test-Path -Path $script:ELEMENT_DIR -PathType Container)) {
        Write-LogWarn "要素类型模块目录不存在: $($script:ELEMENT_DIR)"
        Write-LogInfo "提示：模块将在后续任务中创建（T017-T019）"
        # 第一阶段：不强制要求模块存在，允许框架模式运行
    }
    
    # 加载扫描函数模块
    $scanModule = Join-Path $script:ELEMENT_DIR "scan-$Target.ps1"
    if (Test-Path -Path $scanModule -PathType Leaf) {
        . $scanModule
        if (-not (Get-Command $script:ELEMENT_SCANNER -ErrorAction SilentlyContinue)) {
            Write-LogWarn "扫描函数不存在: $($script:ELEMENT_SCANNER) (在模块 $scanModule 中)"
            Write-LogInfo "提示：扫描函数将在后续任务中实现（T017）"
        } else {
            Write-LogDebug "已加载扫描模块: $scanModule"
        }
    } else {
        Write-LogWarn "扫描模块不存在: $scanModule (将在后续任务中实现，T017)"
    }
    
    # 加载分析函数模块
    $analyzeModule = Join-Path $script:ELEMENT_DIR "analyze-$Target.ps1"
    if (Test-Path -Path $analyzeModule -PathType Leaf) {
        . $analyzeModule
        if (-not (Get-Command $script:ELEMENT_ANALYZER -ErrorAction SilentlyContinue)) {
            Write-LogWarn "分析函数不存在: $($script:ELEMENT_ANALYZER) (在模块 $analyzeModule 中)"
            Write-LogInfo "提示：分析函数将在后续任务中实现（T018）"
        } else {
            Write-LogDebug "已加载分析模块: $analyzeModule"
        }
    } else {
        Write-LogWarn "分析模块不存在: $analyzeModule (将在后续任务中实现，T018)"
    }
    
    # 加载验证函数模块（如果存在且启用验证）
    if ($script:VALIDATE -and -not [string]::IsNullOrEmpty($script:ELEMENT_VALIDATOR) -and $script:ELEMENT_VALIDATOR -ne "null") {
        $validateModule = Join-Path $script:ELEMENT_DIR "validate-$Target.ps1"
        if (Test-Path -Path $validateModule -PathType Leaf) {
            . $validateModule
            if (-not (Get-Command $script:ELEMENT_VALIDATOR -ErrorAction SilentlyContinue)) {
                Write-LogWarn "验证函数不存在: $($script:ELEMENT_VALIDATOR) (在模块 $validateModule 中)"
            } else {
                Write-LogDebug "已加载验证模块: $validateModule"
            }
        } else {
            Write-LogWarn "验证模块不存在: $validateModule (将在后续任务中实现)"
        }
    }
    
    # 加载合并函数模块（如果启用增量合并）
    if ($script:INCREMENTAL -and $script:MERGE -and -not [string]::IsNullOrEmpty($script:ELEMENT_MERGER) -and $script:ELEMENT_MERGER -ne "null") {
        $mergeModule = Join-Path $script:ELEMENT_DIR "merge-$Target.ps1"
        if (Test-Path -Path $mergeModule -PathType Leaf) {
            . $mergeModule
            if (-not (Get-Command $script:ELEMENT_MERGER -ErrorAction SilentlyContinue)) {
                Write-LogWarn "合并函数不存在: $($script:ELEMENT_MERGER) (在模块 $mergeModule 中)"
            } else {
                Write-LogDebug "已加载合并模块: $mergeModule"
            }
        } else {
            Write-LogWarn "合并模块不存在: $mergeModule (将在后续任务中实现)"
        }
    }
    
    Write-LogDebug "要素类型分发完成: $($script:ELEMENT_NAME) ($Target)"
    return $true
}

# 主函数（第一阶段：基础框架）
function Main {
    param([string[]]$Arguments)

    Write-LogInfo "开始 reverse 命令执行..."

    # 解析参数
    Parse-Args -Arguments $Arguments

    # 验证参数
    Test-Params

    # 解析范围
    if (-not (Resolve-Scope -PathsStr $script:PATHS -FilesStr $script:FILES -RepoRoot $REPO_ROOT)) {
        Write-LogError "范围解析失败"
        exit $SCRIPT:ERROR_INVALID_PARAMS
    }

    # 要素类型分发
    if (-not (Invoke-ElementTypeDispatch -Target $script:TARGET -RepoRoot $REPO_ROOT -ScriptDir $ScriptDir)) {
        Write-LogError "要素类型分发失败"
        exit $SCRIPT:ERROR_INVALID_TARGET
    }

    # 第一阶段：只实现框架，具体功能在后续任务中实现
    Write-LogInfo "目标要素类型: $script:ELEMENT_NAME ($script:TARGET)"
    Write-LogInfo "扫描路径: $($script:RESOLVED_PATHS.Count) 个路径"
    Write-LogInfo "扫描文件: $($script:RESOLVED_FILES.Count) 个文件"

    Write-LogWarn "警告：这是第一阶段的基础框架，具体功能将在后续任务中实现"
    Write-LogInfo "功能开发进度请参考任务清单：omni-infra/design/omni_reverse_tasks.md"

    # TODO: 后续阶段实现
    # - 调用扫描和分析函数（T017-T019）
    # - AI 分析任务调用（T020-T024）
    # - 用户交互确认（T025-T027）
    # - 模板渲染（T028-T030）
    # - 输出处理（T031-T034）

    Write-LogSuccess "命令执行完成（框架模式）"
}

# 处理辅助命令（用于 AI Agent 调用模板函数，在主函数之前处理）
# 这些命令不进入主流程，直接执行并退出
if ($args.Count -gt 0) {
    switch ($args[0]) {
        '--load-few-shot-template' {
            if ($args.Count -lt 2) {
                Write-LogError "参数错误: --load-few-shot-template 需要指定仓库根目录"
                exit $SCRIPT:ERROR_INVALID_PARAMS
            }
            Load-FewShotTemplate -RepoRoot $args[1]
            exit $LASTEXITCODE
        }
        '--extract-identification-rules' {
            if ($args.Count -lt 3) {
                Write-LogError "参数错误: --extract-identification-rules 需要指定模板文件和接口类型"
                exit $SCRIPT:ERROR_INVALID_PARAMS
            }
            Extract-IdentificationRules -TemplateFile $args[1] -InterfaceType $args[2]
            exit $LASTEXITCODE
        }
        '--extract-constraints' {
            if ($args.Count -lt 3) {
                Write-LogError "参数错误: --extract-constraints 需要指定模板文件和接口类型"
                exit $SCRIPT:ERROR_INVALID_PARAMS
            }
            Extract-Constraints -TemplateFile $args[1] -InterfaceType $args[2]
            exit $LASTEXITCODE
        }
        '--extract-format-definition' {
            if ($args.Count -lt 2) {
                Write-LogError "参数错误: --extract-format-definition 需要指定模板文件"
                exit $SCRIPT:ERROR_INVALID_PARAMS
            }
            Extract-FormatDefinition -TemplateFile $args[1]
            exit $LASTEXITCODE
        }
        '--extract-interface-types' {
            if ($args.Count -lt 2) {
                Write-LogError "参数错误: --extract-interface-types 需要指定模板文件"
                exit $SCRIPT:ERROR_INVALID_PARAMS
            }
            Extract-InterfaceTypes -TemplateFile $args[1]
            exit $LASTEXITCODE
        }
        '--format-rules-for-prompt' {
            if ($args.Count -lt 3) {
                Write-LogError "参数错误: --format-rules-for-prompt 需要指定规则 JSON、接口类型和约束规则（可选）"
                exit $SCRIPT:ERROR_INVALID_PARAMS
            }
            $constraintsJson = if ($args.Count -ge 4) { $args[3] } else { "[]" }
            $convertedConstraintsJson = if ($args.Count -ge 5) { $args[4] } else { "[]" }
            Format-RulesForPrompt -RulesJson $args[1] -InterfaceType $args[2] -ConstraintsJson $constraintsJson -ConvertedConstraintsJson $convertedConstraintsJson
            exit $LASTEXITCODE
        }
    }
}

# 执行主函数
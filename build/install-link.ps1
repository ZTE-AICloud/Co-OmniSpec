#!/usr/bin/env pwsh

# OmniSpec 软链接安装脚本 (Windows/PowerShell 版本)
# 功能：将 src/agent/commands 和 src/specify 目录软链接到目标代码工程路径
# 详细使用说明请运行: ./install-link.ps1 -h 或 ./install-link.ps1 --help

$ErrorActionPreference = 'Stop'

# 显示使用说明
function Show-Usage {
    $scriptName = if ($PSCommandPath) { Split-Path -Leaf $PSCommandPath } else { "install-link.ps1" }
    Write-Host @"
OmniSpec 软链接安装脚本

使用方法:
  .\$scriptName [选项]

功能说明:
  1. 提示用户输入目标项目目录
  2. 提示用户选择 agent 类型（AI-IDE、cursor、claude code）
  3. 在目标项目目录下创建对应的目录（.flow、.cursor 或 .claude）
  4. 将 OmniSpec/src/agent/commands 软链接到 项目目录/.{agent_type}/commands
  5. 将 OmniSpec/specify 软链接到 项目目录/.specify

Agent 类型映射:
  - AI-IDE      -> .flow 目录
  - cursor      -> .cursor 目录
  - claude code -> .claude 目录

示例:
  .\$scriptName
  .\$scriptName -p C:\path\to\project -a cursor
  .\$scriptName --project-dir C:\path\to\project --agent-type cursor

选项:
  -h, --help              显示此帮助信息
  -p, --project-dir DIR   指定目标项目目录（可选，不指定则提示输入）
  -a, --agent-type TYPE   指定 agent 类型（可选，不指定则提示选择）
                         支持的值: AI-IDE, cursor, claude-code

注意事项:
  - 如果目标目录已存在，会提示用户确认是否覆盖
  - 如果软链接已存在，会提示用户确认是否重新创建
  - 脚本必须在 OmniSpec 代码库根目录下执行
  - 创建符号链接可能需要管理员权限（取决于系统策略）

"@
}

# 获取脚本所在目录
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
# SOURCE_DIR 指向 build 的父目录（OmniSpec），以便找到 agent 和 specify 目录
$SOURCE_DIR = Split-Path -Parent $SCRIPT_DIR

$SOURCE_AGENT_COMMANDS_DIR = Join-Path $SOURCE_DIR "src\agent\commands"
$SOURCE_SPECIFY_DIR = Join-Path $SOURCE_DIR "src\specify"

# 打印信息
function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Green
}

function Write-Warn {
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Write-Error{
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

# 打印分隔线
function Write-Separator {
    Write-Host "=========================================="
}

# 打印标题
function Write-Title {
    param([string]$Title)
    Write-Host $Title -ForegroundColor Cyan
}

# 检查源目录是否存在
function Test-SourceDirs {
    if (-not (Test-Path -Path $SOURCE_AGENT_COMMANDS_DIR -PathType Container)) {
        Write-Error "src/agent/commands 目录不存在: $SOURCE_AGENT_COMMANDS_DIR"
        exit 1
    }
    
    if (-not (Test-Path -Path $SOURCE_SPECIFY_DIR -PathType Container)) {
        Write-Error"specify 目录不存在: $SOURCE_SPECIFY_DIR"
        exit 1
    }
}

# 验证并获取目标项目目录
function Get-TargetProjectDir {
    param([string]$InputDir)
    
    if ([string]::IsNullOrWhiteSpace($InputDir)) {
        return $null
    }
    
    # 如果路径不存在
    if (-not (Test-Path -Path $InputDir -PathType Container)) {
        return $null
    }
    
    # 转换为绝对路径
    $absPath = (Resolve-Path -Path $InputDir).Path
    return $absPath
}

# 根据 agent 类型获取目录名
function Get-AgentDirName {
    param([string]$AgentType)
    
    switch ($AgentType) {
        "AI-IDE" {
            return ".flow"
        }
        "cursor" {
            return ".cursor"
        }
        "claude code" {
            return ".claude"
        }
        "claude-code" {
            return ".claude"
        }
        default {
            Write-Error"不支持的 agent 类型: $AgentType"
            return $null
        }
    }
}

# 去除字符串首尾空格
function Trim-String {
    param([string]$String)
    return $String.Trim()
}

# 提示用户确认
function Confirm-Action {
    param([string]$Message)
    
    Write-Host $Message -ForegroundColor Yellow -NoNewline
    $response = Read-Host
    return $response -match '^[Yy]$'
}

# 根据序号获取 agent 类型
function Get-AgentTypeByNumber {
    param([int]$Number)
    
    switch ($Number) {
        1 { return "AI-IDE" }
        2 { return "cursor" }
        3 { return "claude code" }
        default { return $null }
    }
}

# 提示用户输入项目目录
function Prompt-ProjectDir {
    while ($true) {
        Write-Host ""
        Write-Host "步骤 1/2: 输入项目代码目录" -ForegroundColor Cyan
        Write-Host "请输出项目代码目录：" -ForegroundColor Blue -NoNewline
        $projectDir = Read-Host
        
        # 去除首尾空格
        $projectDir = Trim-String $projectDir
        
        if ([string]::IsNullOrWhiteSpace($projectDir)) {
            Write-Error"项目目录不能为空，请重新输入"
            Write-Host ""
            continue
        }
        
        $absDir = Get-TargetProjectDir -InputDir $projectDir
        if ($absDir) {
            Write-Host ""
            Write-Info "项目目录验证成功: $absDir"
            return $absDir
        } else {
            Write-Error"项目目录不存在或无法访问: $projectDir"
            if (-not (Confirm-Action "是否重新输入？(Y/n):")) {
                return $null
            }
            Write-Host ""
        }
    }
}

# 提示用户选择 agent 类型
function Prompt-AgentType {
    Write-Host ""
    Write-Host "步骤 2/2: 选择 Agent 类型" -ForegroundColor Cyan
    Write-Host "请选择 agent 类型:" -ForegroundColor Blue
    Write-Host ""
    Write-Host "  1) AI-IDE"
    Write-Host "  2) cursor"
    Write-Host "  3) claude code"
    Write-Host ""
    
    while ($true) {
        Write-Host "请输入选项序号 (1-3): " -ForegroundColor Blue -NoNewline
        $choice = Read-Host
        
        # 去除首尾空格
        $choice = Trim-String $choice
        
        if ([string]::IsNullOrWhiteSpace($choice)) {
            Write-Error"选项不能为空，请重新输入"
            Write-Host ""
            continue
        }
        
        $choiceNum = 0
        if (-not [int]::TryParse($choice, [ref]$choiceNum)) {
            Write-Error"无效的选项，请输入 1、2 或 3"
            Write-Host ""
            continue
        }
        
        $agentType = Get-AgentTypeByNumber -Number $choiceNum
        if ($agentType) {
            Write-Host ""
            Write-Info "已选择 Agent 类型: $agentType"
            return $agentType
        } else {
            Write-Error"无效的选项，请输入 1、2 或 3"
            Write-Host ""
        }
    }
}

# 创建目录（如果不存在）
function New-DirectoryIfNotExists {
    param(
        [string]$DirPath,
        [string]$DirName
    )
    
    if (Test-Path -Path $DirPath -PathType Container) {
        Write-Info "$DirName 目录已存在: $DirPath"
        return
    }
    
    Write-Info "正在创建 $DirName 目录: $DirPath"
    try {
        New-Item -ItemType Directory -Path $DirPath -Force | Out-Null
        Write-Success "$DirName 目录创建成功"
    } catch {
        Write-Error"创建目录失败: $_"
        exit 1
    }
}

# 创建软链接
function New-Symlink {
    param(
        [string]$SourcePath,
        [string]$TargetPath,
        [string]$LinkName
    )
    
    # 转换为绝对路径
    $sourceAbs = (Resolve-Path -Path $SourcePath).Path
    
    # 如果目标路径已存在
    if (Test-Path -Path $TargetPath) {
        # 检查是否是软链接
        try {
            $item = Get-Item -Path $TargetPath -Force -ErrorAction Stop
            if ($item.LinkType -eq "SymbolicLink") {
                $currentTarget = $item.Target
                # 处理相对路径和绝对路径
                $currentTargetAbs = if ($currentTarget) {
                    if ([System.IO.Path]::IsPathRooted($currentTarget)) {
                        $currentTarget
                    } else {
                        $parentDir = Split-Path -Parent $TargetPath
                        (Resolve-Path -Path (Join-Path $parentDir $currentTarget) -ErrorAction SilentlyContinue).Path
                    }
                } else { $null }
                
                # 标准化路径比较
                $sourceAbsNormalized = [System.IO.Path]::GetFullPath($sourceAbs)
                $currentTargetAbsNormalized = if ($currentTargetAbs) { [System.IO.Path]::GetFullPath($currentTargetAbs) } else { $null }
                
                if ($currentTargetAbsNormalized -eq $sourceAbsNormalized) {
                    Write-Info "$LinkName 软链接已存在且指向正确: $TargetPath"
                    return
                } else {
                    Write-Warn "$LinkName 软链接已存在但指向不同的位置: $TargetPath"
                    Write-Warn "  当前指向: $currentTarget"
                    Write-Warn "  应该指向: $sourceAbs"
                    if (-not (Confirm-Action "是否删除并重新创建软链接？(y/N):")) {
                        Write-Warn "跳过 $LinkName 软链接的创建"
                        return
                    }
                    Remove-Item -Path $TargetPath -Force
                }
            } else {
                # 是文件或目录，不是软链接
                Write-Warn "$LinkName 目标路径已存在且不是软链接: $TargetPath"
                if (-not (Confirm-Action "是否删除并创建软链接？(y/N):")) {
                    Write-Warn "跳过 $LinkName 软链接的创建"
                    return
                }
                if ($item.PSIsContainer) {
                    Remove-Item -Path $TargetPath -Recurse -Force
                } else {
                    Remove-Item -Path $TargetPath -Force
                }
            }
        } catch {
            # 如果无法获取项目信息，尝试删除
            Write-Warn "$LinkName 目标路径已存在但无法检查类型: $TargetPath"
            if (-not (Confirm-Action "是否删除并创建软链接？(y/N):")) {
                Write-Warn "跳过 $LinkName 软链接的创建"
                return
            }
            Remove-Item -Path $TargetPath -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
    
    # 创建软链接
    Write-Info "正在创建 $LinkName 软链接..."
    Write-Info "  源路径: $SourcePath"
    Write-Info "  目标路径: $TargetPath"
    
    # 确保目标路径的父目录存在
    $targetParent = Split-Path -Parent $TargetPath
    if (-not (Test-Path -Path $targetParent -PathType Container)) {
        New-Item -ItemType Directory -Path $targetParent -Force | Out-Null
    }
    
    # 转换为绝对路径
    $targetAbs = if ([System.IO.Path]::IsPathRooted($TargetPath)) {
        $TargetPath
    } else {
        $currentDir = Get-Location
        [System.IO.Path]::GetFullPath((Join-Path $currentDir.Path $TargetPath))
    }
    
    # 标准化路径
    $sourceAbsNormalized = [System.IO.Path]::GetFullPath($sourceAbs)
    $targetAbsNormalized = [System.IO.Path]::GetFullPath($targetAbs)
    
    try {
        # 使用 New-Item 创建符号链接
        New-Item -ItemType SymbolicLink -Path $targetAbsNormalized -Target $sourceAbsNormalized -Force | Out-Null
        Write-Success "$LinkName 软链接创建成功"
    } catch {
        # 如果 New-Item 失败，尝试使用 mklink（可能需要管理员权限）
        Write-Warn "使用 New-Item 创建符号链接失败，尝试使用 mklink: $_"
        try {
            # 使用 mklink 创建目录符号链接
            $mklinkCmd = "cmd /c mklink /D `"$targetAbsNormalized`" `"$sourceAbsNormalized`""
            $result = Invoke-Expression $mklinkCmd 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Success "$LinkName 软链接创建成功"
            } else {
                Write-Error"创建符号链接失败。可能需要管理员权限。"
                Write-Error"错误信息: $result"
                Write-Error"请以管理员身份运行 PowerShell，或启用开发人员模式。"
                Write-Error"启用开发人员模式：设置 -> 更新和安全 -> 开发者选项 -> 开发人员模式"
                exit 1
            }
        } catch {
            Write-Error"创建符号链接失败: $_"
            Write-Error"请确保："
            Write-Error"  1. 以管理员身份运行 PowerShell，或"
            Write-Error"  2. 在 Windows 设置中启用开发人员模式（设置 -> 更新和安全 -> 开发者选项 -> 开发人员模式）"
            exit 1
        }
    }
}

# 主函数
function Main {
    param(
        [string]$ProjectDir = "",
        [string]$AgentType = ""
    )
    
    # 解析命令行参数
    $argsList = $args
    for ($i = 0; $i -lt $argsList.Length; $i++) {
        $arg = $argsList[$i]
        switch ($arg) {
            { $_ -in "-h", "--help" } {
                Show-Usage
                exit 0
            }
            { $_ -in "-p", "--project-dir" } {
                if ($i + 1 -ge $argsList.Length) {
                    Write-Error"选项 $arg 需要指定项目目录"
                    Show-Usage
                    exit 1
                }
                $ProjectDir = $argsList[$i + 1]
                $i++
            }
            { $_ -in "-a", "--agent-type" } {
                if ($i + 1 -ge $argsList.Length) {
                    Write-Error"选项 $arg 需要指定 agent 类型"
                    Show-Usage
                    exit 1
                }
                $AgentType = $argsList[$i + 1]
                $i++
            }
            default {
                Write-Error"未知选项: $arg"
                Show-Usage
                exit 1
            }
        }
    }
    
    # 显示标题
    Write-Separator
    Write-Title "  OmniSpec 软链接安装脚本"
    Write-Separator
    Write-Host ""
    
    # 检查源目录
    Write-Info "正在检查源目录..."
    Test-SourceDirs
    Write-Success "源目录检查通过"
    Write-Host ""
    
    # 获取目标项目目录
    if ([string]::IsNullOrWhiteSpace($ProjectDir)) {
        $ProjectDir = Prompt-ProjectDir
        if ([string]::IsNullOrWhiteSpace($ProjectDir)) {
            Write-Error"用户取消操作"
            exit 1
        }
    } else {
        Write-Info "使用命令行参数指定的项目目录: $ProjectDir"
        $validatedDir = Get-TargetProjectDir -InputDir $ProjectDir
        if (-not $validatedDir) {
            Write-Error"无效的目标项目目录: $ProjectDir"
            exit 1
        }
        $ProjectDir = $validatedDir
        Write-Info "项目目录验证成功: $ProjectDir"
    }
    
    # 获取 agent 类型
    if ([string]::IsNullOrWhiteSpace($AgentType)) {
        $AgentType = Prompt-AgentType
    } else {
        Write-Info "使用命令行参数指定的 Agent 类型: $AgentType"
    }
    
    # 验证 agent 类型并获取目录名
    $agentDirName = Get-AgentDirName -AgentType $AgentType
    if (-not $agentDirName) {
        exit 1
    }
    
    Write-Host ""
    Write-Separator
    Write-Info "开始安装..."
    Write-Separator
    Write-Host ""
    Write-Info "配置信息:"
    Write-Info "  项目目录: $ProjectDir"
    Write-Info "  Agent 类型: $AgentType"
    Write-Info "  Agent 目录: $agentDirName"
    Write-Host ""
    
    # 创建 agent 目录
    $agentDir = Join-Path $ProjectDir $agentDirName
    New-DirectoryIfNotExists -DirPath $agentDir -DirName "Agent ($agentDirName)"
    Write-Host ""
    
    # 创建软链接：src/agent/commands -> .{agent_type}/commands
    $commandsLinkTarget = Join-Path $agentDir "commands"
    New-Symlink `
        -SourcePath $SOURCE_AGENT_COMMANDS_DIR `
        -TargetPath $commandsLinkTarget `
        -LinkName "src/agent/commands"
    Write-Host ""
    
    # 创建软链接：specify -> .specify
    $specifyLinkTarget = Join-Path $ProjectDir ".specify"
    New-Symlink `
        -SourcePath $SOURCE_SPECIFY_DIR `
        -TargetPath $specifyLinkTarget `
        -LinkName "specify"
    Write-Host ""
    
    Write-Separator
    Write-Success "安装完成！"
    Write-Separator
    Write-Host ""
    Write-Info "安装摘要:"
    Write-Info "  项目目录: $ProjectDir"
    Write-Info "  Agent 目录: $agentDir"
    Write-Info "  软链接:"
    Write-Info "    - $commandsLinkTarget -> $SOURCE_AGENT_COMMANDS_DIR"
    Write-Info "    - $specifyLinkTarget -> $SOURCE_SPECIFY_DIR"
    Write-Host ""
}

# 执行主函数
Main @args

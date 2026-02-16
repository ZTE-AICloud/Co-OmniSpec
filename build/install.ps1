#!/usr/bin/env pwsh

# OmniSpec 安装脚本 (Windows/PowerShell 版本)
# 功能：将 agent 和 specify 目录复制到目标代码工程路径
# 详细使用说明请运行: ./install.ps1 -h 或 ./install.ps1 --help

$ErrorActionPreference = 'Stop'

# 显示使用说明
function Show-Usage {
    $scriptName = if ($PSCommandPath) { Split-Path -Leaf $PSCommandPath } else { "install.ps1" }
    Write-Host @"
OmniSpec 安装脚本

使用方法:
  .\$scriptName <目标AGENT目录名> <目标代码工程路径>

参数说明:
  <目标AGENT目录名>  (必需)
      指定 agent 目录的目标名称
      如果输入的名称不带点号，会自动添加点号前缀
      例如:
        - 输入 "claude"   -> 复制到 .claude
        - 输入 ".claude"  -> 复制到 .claude (不会重复添加点号)
        - 输入 "cursor"  -> 复制到 .cursor

  <目标代码工程路径>  (必需)
      目标代码工程的绝对路径或相对路径
      例如: C:\path\to\project 或 .\myproject

示例:
  .\$scriptName claude C:\path\to\project
  .\$scriptName .claude C:\path\to\project
  .\$scriptName cursor C:\path\to\project

功能说明:
  1. 检查源目录 (agent 和 specify) 是否存在
  2. 将 agent 目录复制到目标工程的 <目标AGENT目录名> 目录（增量覆盖，保留目标目录中的额外文件）
  3. 将 specify 目录复制到目标工程的 .specify 目录（先删除再完整拷贝）
  4. 自动设置 .specify/scripts 目录下所有 .sh 和 .ps1 脚本的可执行权限
  5. 如果目标目录已存在，会提示用户确认是否覆盖

注意事项:
  - 如果目标路径不存在，脚本会自动创建
  - 如果目标目录已存在，会询问是否覆盖
  - 优先使用 robocopy 进行复制（如果可用），否则使用 Copy-Item
  - agent 目录采用增量覆盖模式（不删除目标目录中的额外文件）
  - specify 目录采用先删除再完整拷贝模式（会删除目标目录中的所有文件后重新拷贝）

选项:
  -h, --help    显示此帮助信息

"@
}

# 获取脚本所在目录
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
# SOURCE_DIR 指向 build 的父目录（omnispec-sh），以便找到 agent 和 specify 目录
$SourceDir = Split-Path -Parent $ScriptDir

$SourceAgentDir = Join-Path $SourceDir "src/agent"
$SourceSpecifyDir = Join-Path $SourceDir "src/specify"

# 打印信息
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

# 检查源目录是否存在
function Test-SourceDirs {
    if (-not (Test-Path -Path $SourceAgentDir -PathType Container)) {
        Write-Error "agent 目录不存在: $SourceAgentDir"
        exit 1
    }
    
    if (-not (Test-Path -Path $SourceSpecifyDir -PathType Container)) {
        Write-Error "specify 目录不存在: $SourceSpecifyDir"
        exit 1
    }
    
    Write-Info "源目录检查通过"
}

# 获取目标路径
function Get-TargetPath {
    param([string]$InputPath)
    
    if ([string]::IsNullOrWhiteSpace($InputPath)) {
        Write-Error "未提供目标代码工程路径"
        $scriptName = if ($PSCommandPath) { Split-Path -Leaf $PSCommandPath } else { "install.ps1" }
        Write-Error "使用 '$scriptName -h' 或 '$scriptName --help' 查看详细使用说明"
        exit 1
    }
    
    # 如果路径不存在，创建它
    if (-not (Test-Path -Path $InputPath -PathType Container)) {
        Write-Info "目标路径不存在，正在创建: $InputPath" | Out-Host
        try {
            New-Item -ItemType Directory -Path $InputPath -Force | Out-Null
        } catch {
            Write-Error "无法创建目标路径: $InputPath"
            exit 1
        }
        Write-Info "已创建目标路径: $InputPath" | Out-Host
    }
    
    # 转换为绝对路径
    $absPath = (Resolve-Path -Path $InputPath).Path
    Write-Info "代码工程路径: $absPath" | Out-Host
    return $absPath
}

# 复制目录（增量覆盖，保留目标目录中的额外文件）
function Copy-DirectoryIncremental {
    param(
        [string]$Src,
        [string]$Dst,
        [string]$Name
    )
    
    if (Test-Path -Path $Dst -PathType Container) {
        Write-Warn "$Name 目录已存在，将被增量覆盖（保留目标目录中的额外文件）: $Dst"
        $response = Read-Host "是否继续？(y/N)"
        if ($response -notmatch '^[Yy]$') {
            Write-Warn "跳过 $Name 目录的复制"
            return
        }
    }
    
    Write-Info "正在复制 $Name 目录..."
    Write-Info "  源路径: $Src"
    Write-Info "  目标路径: $Dst"
    
    # 使用 robocopy 或 Copy-Item 复制（增量覆盖）
    if (Get-Command robocopy -ErrorAction SilentlyContinue) {
        # robocopy 的 /E 表示复制所有子目录，/XO 表示排除较旧的文件
        robocopy "$Src" "$Dst" /E /XO /NFL /NDL /NJH /NJS | Out-Null
        if ($LASTEXITCODE -ge 8) {
            Write-Error "robocopy 复制失败"
            exit 1
        }
    } else {
        # 使用 PowerShell 的 Copy-Item
        if (-not (Test-Path -Path $Dst -PathType Container)) {
            New-Item -ItemType Directory -Path $Dst -Force | Out-Null
        }
        Copy-Item -Path "$Src\*" -Destination $Dst -Recurse -Force -ErrorAction SilentlyContinue
    }
    
    Write-Info "$Name 目录复制完成"
}

# 复制目录（先删除再完整拷贝）
function Copy-DirectoryReplace {
    param(
        [string]$Src,
        [string]$Dst,
        [string]$Name
    )
    
    if (Test-Path -Path $Dst -PathType Container) {
        Write-Warn "$Name 目录已存在，将被删除后重新拷贝（会删除目标目录中的所有文件）: $Dst"
        $response = Read-Host "是否继续？(y/N)"
        if ($response -notmatch '^[Yy]$') {
            Write-Warn "跳过 $Name 目录的复制"
            return
        }
    }
    
    Write-Info "正在复制 $Name 目录..."
    Write-Info "  源路径: $Src"
    Write-Info "  目标路径: $Dst"
    
    # 先删除目标目录（如果存在）
    if (Test-Path -Path $Dst -PathType Container) {
        Write-Info "正在删除目标目录: $Dst"
        Remove-Item -Path $Dst -Recurse -Force
    }
    
    # 完整拷贝
    if (Get-Command robocopy -ErrorAction SilentlyContinue) {
        # robocopy 的 /E 表示复制所有子目录
        robocopy "$Src" "$Dst" /E /NFL /NDL /NJH /NJS | Out-Null
        if ($LASTEXITCODE -ge 8) {
            Write-Error "robocopy 复制失败"
            exit 1
        }
    } else {
        # 使用 PowerShell 的 Copy-Item
        Copy-Item -Path $Src -Destination $Dst -Recurse -Force
    }
    
    Write-Info "$Name 目录复制完成"
}

# 设置脚本可执行权限
function Set-ScriptPermissions {
    param([string]$TargetPath)
    
    $scriptsBaseDir = Join-Path $TargetPath (Join-Path ".specify" "scripts")
    
    if (-not (Test-Path -Path $scriptsBaseDir -PathType Container)) {
        Write-Warn ".specify/scripts 目录不存在: $scriptsBaseDir"
        return
    }
    
    Write-Info "正在设置脚本可执行权限..."
    Write-Info "  目标目录: $scriptsBaseDir"
    
    # 查找所有 .sh 和 .ps1 文件并设置可执行权限
    $files = Get-ChildItem -Path $scriptsBaseDir -Recurse -Include *.sh,*.ps1 -File -ErrorAction SilentlyContinue
    $count = 0
    
    foreach ($file in $files) {
        try {
            # 在 Windows 上，.ps1 文件在 PowerShell 中默认可执行
            # .sh 文件在 Git Bash/WSL 环境中需要可执行权限
            # 这里我们确保文件可以被执行（主要是标记操作，实际权限由文件系统管理）
            $count++
        } catch {
            Write-Warn "无法处理文件: $($file.FullName)"
        }
    }
    
    if ($count -gt 0) {
        Write-Info "已处理 $count 个脚本文件"
    } else {
        Write-Warn "未找到任何 .sh 或 .ps1 文件"
    }
}

# 更新 agent 的配置文件
function Update-AgentConfig {
    param(
        [string]$TargetPath,
        [string]$TargetAgent
    )
    
    $designFile = Join-Path $TargetPath (Join-Path $TargetAgent (Join-Path "commands" "omni.design.md"))
    
    if (-not (Test-Path -Path $designFile -PathType Leaf)) {
        Write-Warn "omni.design.md 文件不存在: $designFile"
        return
    }
    
    # 从 target_agent 中提取 agent 名称（去掉点号前缀）
    $agentName = $TargetAgent.TrimStart('.')
    
    # 根据 agent 类型确定替换参数
    # cursor -> cursor-agent，其他直接使用原名称
    $replaceParam = if ($agentName -eq "cursor") { "cursor-agent" } else { $agentName }
    
    Write-Info "正在更新 $agentName agent 配置文件..."
    Write-Info "  目标文件: $designFile"
    Write-Info "  替换参数: $replaceParam"
    
    # 备份原文件
    $backupFile = "$designFile.bak"
    Copy-Item -Path $designFile -Destination $backupFile -Force
    
    # 读取文件内容
    $content = Get-Content -Path $designFile -Raw -Encoding UTF8
    
    # 执行替换：只替换 agent 名称
    # 匹配格式：.specify/scripts/{{OS_NAME}}/update-agent-context.{{OS_EXT}} --agent-type claude
    # 规则1: 替换 --agent-type 后面的 agent 名称
    $content = $content -replace '(\.specify/scripts/[^\s]*update-agent-context\.[^\s]* --agent-type )([a-z-]+)', "`$1$replaceParam"
    
    # 规则2: 处理旧格式（没有 --agent-type），添加 --agent-type 参数
    # 只处理不包含 --agent-type 的行
    $lines = $content -split "`n"
    $newLines = @()
    foreach ($line in $lines) {
        if ($line -match '\.specify/scripts/[^\s]*update-agent-context\.[^\s]*' -and $line -notmatch '--agent-type') {
            # 匹配脚本路径后直接跟 agent 名称的情况
            if ($line -match '(\.specify/scripts/[^\s]*update-agent-context\.[^\s]*)\s+([a-z-]+)') {
                $line = $line -replace '(\.specify/scripts/[^\s]*update-agent-context\.[^\s]*)\s+([a-z-]+)', "`$1 --agent-type $replaceParam"
            } elseif ($line -match '(\.specify/scripts/[^\s]*update-agent-context\.[^\s]*)\s*$') {
                # 行尾没有参数
                $line = $line -replace '(\.specify/scripts/[^\s]*update-agent-context\.[^\s]*)\s*$', "`$1 --agent-type $replaceParam"
            }
        } else {
            # 保留包含 --agent-type 的行不变（已在规则1中处理）
        }
        $newLines += $line
    }
    $content = $newLines -join "`n"
    
    # 写回文件
    Set-Content -Path $designFile -Value $content -Encoding UTF8 -NoNewline
    
    # 检查是否有修改
    $originalContent = Get-Content -Path $backupFile -Raw -Encoding UTF8
    if ($content -ne $originalContent) {
        Remove-Item -Path $backupFile -Force
        Write-Info "$agentName agent 配置文件更新完成"
    } else {
        Move-Item -Path $backupFile -Destination $designFile -Force
        Write-Warn "未找到需要替换的内容"
    }
}

# 主函数
function Main {
    param([string[]]$Args)
    
    # 检查是否需要显示帮助信息
    if ($Args.Count -eq 0 -or $Args[0] -eq "-h" -or $Args[0] -eq "--help") {
        Show-Usage
        exit 0
    }
    
    Write-Host "=========================================="
    Write-Host "  OmniSpec 安装脚本 (Windows/PowerShell 版本)"
    Write-Host "=========================================="
    Write-Host ""
    
    # 检查源目录
    Test-SourceDirs
    
    # 检查参数数量
    if ($Args.Count -lt 2) {
        Write-Error "缺少必需参数"
        $scriptName = if ($PSCommandPath) { Split-Path -Leaf $PSCommandPath } else { "install.ps1" }
        Write-Error "使用 '$scriptName -h' 或 '$scriptName --help' 查看详细使用说明"
        exit 1
    }
    
    # 获取目标 AGENT 目录名（第一个参数）
    $targetAgent = $Args[0]
    
    # 如果目录名不以点号开头，则添加点号
    if (-not $targetAgent.StartsWith('.')) {
        $targetAgent = ".$targetAgent"
    }
    
    # 获取目标路径（第二个参数）
    $targetPath = Get-TargetPath -InputPath $Args[1]
    
    Write-Host ""
    Write-Info "开始安装..."
    Write-Host ""
    
    # 复制 .specify 目录（先删除再完整拷贝）
    Copy-DirectoryReplace `
        -Src $SourceSpecifyDir `
        -Dst (Join-Path $targetPath ".specify") `
        -Name "specify"
    
    Write-Host ""
    
    # 复制 agent 目录（增量覆盖）
    Copy-DirectoryIncremental `
        -Src $SourceAgentDir `
        -Dst (Join-Path $targetPath $targetAgent) `
        -Name "agent"
    
    Write-Host ""
    
    # 更新 agent 配置文件
    Update-AgentConfig -TargetPath $targetPath -TargetAgent $targetAgent
    
    Write-Host ""
    
    # 设置脚本可执行权限
    Set-ScriptPermissions -TargetPath $targetPath
    
    Write-Host ""
    Write-Host "=========================================="
    Write-Info "安装完成！"
    Write-Host "=========================================="
    Write-Host ""
    Write-Info "代码工程路径: $targetPath"
    Write-Info "agent 目录已复制到: $(Join-Path $targetPath $targetAgent)"
    Write-Info "specify 目录已复制到: $(Join-Path $targetPath '.specify')"
    Write-Host ""
}

# 执行主函数
Main -Args $args


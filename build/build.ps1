#!/usr/bin/env pwsh

# OmniSpec 构建脚本 (Windows/PowerShell 版本)
# 功能：创建带时间戳的打包目录，运行安装脚本，并压缩为 zip 文件

$ErrorActionPreference = 'Stop'

# 显示使用说明
function Show-Usage {
    $scriptName = if ($PSCommandPath) { Split-Path -Leaf $PSCommandPath } else { "build.ps1" }
    Write-Host @"
OmniSpec 构建脚本

使用方法:
  .\$scriptName [指定AGENT名称] [选项]

参数说明:
  [指定AGENT名称]  (可选)
      指定 agent 名称，默认为 "claude"
      如果输入的名称不带点号，会自动添加点号前缀
      例如:
        - 输入 "claude"   -> 复制到 .claude
        - 输入 ".claude"  -> 复制到 .claude (不会重复添加点号)
        - 输入 "cursor"  -> 复制到 .cursor

  选项:
    -h, --help           显示此帮助信息
    -v, --version <版本> 指定版本号（默认：v1.0.0），必须为三段式格式：vX.Y.Z（如：v1.0.0, v2.1.3）
    -o, --output <路径>  指定输出路径（构建目录和 zip 文件将生成到此路径）
    --clean, --remove    压缩完成后删除构建目录（默认不删除）

示例:
  # 使用默认的 claude，不删除构建目录
  .\$scriptName

  # 指定自定义的 agent
  .\$scriptName claude
  .\$scriptName .claude
  .\$scriptName cursor

  # 指定版本号
  .\$scriptName -Version v2.0.0
  .\$scriptName claude -Version v1.5.3

  # 指定输出路径
  .\$scriptName -Output C:\tmp\builds
  .\$scriptName claude -Output .\output

  # 压缩完成后删除构建目录
  .\$scriptName -Clean
  .\$scriptName claude -Clean
  .\$scriptName -Version v1.0.0 -Output C:\tmp\builds -Clean

功能说明:
  1. 获取当前时间戳（年月日时分秒格式）
  2. 在当前目录下创建 omnispec-version-agent-timestamp 文件夹
  3. 运行安装脚本（install.ps1），将 agent 和 specify 目录复制到 omnispec-version-agent-timestamp 文件夹
  4. 将版本发布说明文件复制到打包目录的 .specify 文件夹
  5. 将 omnispec-version-agent-timestamp 文件夹压缩为 omnispec-version-agent-timestamp.zip 文件
  6. 默认保留构建目录，使用 --clean 选项可删除构建目录

ZIP 文件使用说明:
  生成的 omnispec-version-agent-timestamp.zip 文件使用方法：
  1. cd 到目标代码工程路径
  2. 解压 zip 文件即可直接展开 agent（如.claude） 和 .specify 两个文件夹
     例如: Expand-Archive omnispec-v1.0.0-claude-20251206123456.zip
     解压后会直接在目标路径下得到 agent（如.claude） 和 .specify 文件夹

注意事项:
  - 默认情况下，构建目录会在压缩完成后保留
  - 使用 --clean 或 --remove 选项可以在压缩完成后删除构建目录
  - 构建目录名称格式：omnispec-version-agent-timestamp

"@
}

# 获取脚本所在目录
$SCRIPT_DIR = Split-Path -Parent $PSCommandPath

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

# 获取安装脚本路径
function Get-InstallScript {
    return Join-Path $SCRIPT_DIR "install.ps1"
}

# 检查安装脚本是否存在
function Test-InstallScript {
    param([string]$InstallScript)
    
    $scriptName = Split-Path -Leaf $InstallScript
    
    if (-not (Test-Path $InstallScript)) {
        Write-Error "$scriptName 脚本不存在: $InstallScript"
        exit 1
    }
}

# 获取时间戳（年月日时分秒格式：YYYYMMDDHHMMSS）
function Get-Timestamp {
    return Get-Date -Format "yyyyMMddHHmmss"
}

# 获取统一的名称（用于文件夹和zip文件名：omnispec-version-agent-timestamp）
function Get-BuildName {
    param(
        [string]$AgentName,
        [string]$Timestamp,
        [string]$Version
    )
    
    # 从agent名称中去掉点号前缀
    $agentForName = $AgentName -replace '^\.', ''
    
    # 统一名称格式：omnispec-version-agent-timestamp
    return "omnispec-${Version}-${agentForName}-${Timestamp}"
}

# 复制版本发布说明文件到 .specify 文件夹
function Copy-ReleaseNotes {
    param([string]$BuildDir)
    
    # 源文件路径：build 目录的上一级目录下的 src/specify/版本发布说明.md
    $projectRoot = Split-Path -Parent $SCRIPT_DIR
    $sourceSpecifyDir = Join-Path $projectRoot "src/specify"
    $sourceFile = Join-Path $sourceSpecifyDir "版本发布说明.md"
    $targetSpecifyDir = Join-Path $BuildDir ".specify"
    $targetFile = Join-Path $targetSpecifyDir "版本发布说明.md"
    
    # 检查源文件是否存在
    if (-not (Test-Path $sourceFile)) {
        Write-Warn "版本发布说明文件不存在: $sourceFile"
        Write-Warn "跳过复制版本发布说明文件"
        return
    }
    
    # 确保 .specify 目录存在
    if (-not (Test-Path $targetSpecifyDir)) {
        Write-Info ".specify 目录不存在，正在创建..."
        New-Item -ItemType Directory -Path $targetSpecifyDir -Force | Out-Null
    }
    
    Write-Info "正在复制版本发布说明文件..."
    Write-Info "  源文件: $sourceFile"
    Write-Info "  目标文件: $targetFile"
    
    # 复制文件
    try {
        Copy-Item -Path $sourceFile -Destination $targetFile -Force
        Write-Info "版本发布说明文件已复制: $targetFile"
    } catch {
        Write-Error "复制版本发布说明文件失败: $_.Exception.Message"
        return
    }
}

# 生成安装版本开发视图文件（omni_spec_file_list.md）
function Write-SpecFileList {
    param(
        [string]$BuildDir,
        [string]$AgentName,
        [string]$Version,
        [string]$BuildDate
    )
    
    # 将文件生成到构建目录根目录
    $specFile = Join-Path $BuildDir "omni_spec_file_list.md"

    # 获取相对路径的文件清单（去掉前导的 ./）
    $fileTree = @()
    Push-Location $BuildDir
    try {
        $fileTree = Get-ChildItem -Recurse -File | Sort-Object FullName | ForEach-Object {
            $_.FullName.Substring((Get-Location).Path.Length + 1).Replace('\', '/')
        }
    } finally {
        Pop-Location
    }
    
    $fileTreeText = ($fileTree -join "`n")
    
    Write-Info "正在生成安装版本开发视图文件..."
    Write-Info "  目标文件: $specFile"
    Write-Info "  版本号: $Version"
    
    $content = @"
# OmniSpec 安装版本开发视图

## 版本信息

- **版本号**: $Version
- **安装时间**: $BuildDate
- **Agent**: $($AgentName -replace '^\.', '')

## 文件列表

```text
$fileTreeText
```

此文件由 OmniSpec 构建脚本自动生成
"@
    
    Set-Content -Path $specFile -Value $content -Encoding UTF8
    Write-Info "安装版本开发视图文件已生成: $specFile"
}

# 创建打包目录
function New-BuildDirectory {
    param(
        [string]$BuildName,
        [string]$OutputPath
    )
    
    $buildDir = $null
    if (-not [string]::IsNullOrEmpty($OutputPath)) {
        # 如果指定了输出路径，使用输出路径
        if (-not (Test-Path $OutputPath)) {
            Write-Info "输出路径不存在，正在创建: $OutputPath"
            try {
                New-Item -ItemType Directory -Path $OutputPath -Force | Out-Null
            } catch {
                Write-Error "无法创建输出路径: $OutputPath"
                Write-Error $_.Exception.Message
                exit 1
            }
        }
        $absOutputPath = (Resolve-Path -Path $OutputPath -ErrorAction Stop).Path
        $buildDir = Join-Path $absOutputPath $BuildName
    } else {
        # 默认使用脚本所在目录
        $buildDir = Join-Path $SCRIPT_DIR $BuildName
    }
    
    if (Test-Path $buildDir) {
        Write-Error "构建目录已存在: $buildDir"
        exit 1
    }
    
    New-Item -ItemType Directory -Path $buildDir -Force | Out-Null
    Write-Info "创建构建目录: $buildDir"
    return $buildDir
}

# 运行安装脚本
function Invoke-InstallScript {
    param(
        [string]$InstallScript,
        [string]$BuildDir,
        [string]$TargetAgent
    )
    
    Write-Info "运行安装脚本..."
    Write-Info "  脚本: $(Split-Path -Leaf $InstallScript)"
    Write-Info "  目标目录: $BuildDir"
    Write-Info "  Agent 目录名: $TargetAgent"
    
    $scriptExt = [System.IO.Path]::GetExtension($InstallScript)
    
    if ($scriptExt -eq ".sh") {
        # 通过 WSL 或 Git Bash 调用 .sh 脚本
        $scriptPath = $InstallScript -replace '\\', '/'
        if ($scriptPath -match '^([A-Z]):') {
            $driveLetter = $matches[1].ToLower()
            $scriptPath = $scriptPath -replace '^[A-Z]:', "/mnt/$driveLetter"
        }
        
        $buildDirPath = $BuildDir -replace '\\', '/'
        if ($buildDirPath -match '^([A-Z]):') {
            $driveLetter = $matches[1].ToLower()
            $buildDirPath = $buildDirPath -replace '^[A-Z]:', "/mnt/$driveLetter"
        }
        
        # 尝试通过 WSL 调用
        if (Get-Command wsl -ErrorAction SilentlyContinue) {
            try {
                wsl bash $scriptPath $TargetAgent $buildDirPath
                if ($LASTEXITCODE -ne 0) {
                    Write-Error "安装脚本执行失败"
                    exit 1
                }
            } catch {
                Write-Error "无法通过 WSL 执行安装脚本: $_.Exception.Message"
                exit 1
            }
        } elseif (Get-Command bash -ErrorAction SilentlyContinue) {
            # 尝试通过 Git Bash 调用
            try {
                $bashScriptPath = $InstallScript -replace '\\', '/'
                $bashBuildDir = $BuildDir -replace '\\', '/'
                bash $bashScriptPath $TargetAgent $bashBuildDir
                if ($LASTEXITCODE -ne 0) {
                    Write-Error "安装脚本执行失败"
                    exit 1
                }
            } catch {
                Write-Error "无法通过 Git Bash 执行安装脚本: $_.Exception.Message"
                exit 1
            }
        } else {
            Write-Error "无法执行 .sh 脚本，请安装 WSL 或 Git Bash"
            exit 1
        }
    } else {
        # 直接调用 PowerShell 脚本
        try {
            & $InstallScript $TargetAgent $BuildDir
            if (-not $?) {
                Write-Error "安装脚本执行失败"
                exit 1
            }
        } catch {
            Write-Error "无法执行安装脚本: $_.Exception.Message"
            exit 1
        }
    }
}

# 压缩目录
function New-ZipFile {
    param(
        [string]$BuildDir,
        [string]$BuildName,
        [string]$OutputPath
    )
    
    # 生成zip文件名：使用与文件夹相同的名称
    $zipFile = $null
    if (-not [string]::IsNullOrEmpty($OutputPath)) {
        # 如果指定了输出路径，使用输出路径
        $absOutputPath = (Resolve-Path -Path $OutputPath -ErrorAction Stop).Path
        $zipFile = Join-Path $absOutputPath "$BuildName.zip"
    } else {
        # 默认使用脚本所在目录
        $zipFile = Join-Path $SCRIPT_DIR "$BuildName.zip"
    }
    
    if (Test-Path $zipFile) {
        Write-Warn "ZIP 文件已存在，将被覆盖: $zipFile"
        Remove-Item -Path $zipFile -Force
    }
    
    Write-Info "正在压缩目录..."
    Write-Info "  源目录: $BuildDir"
    Write-Info "  目标文件: $zipFile"
    
    # 确保 zip 文件所在目录存在
    $zipDir = Split-Path -Parent $zipFile
    if (-not (Test-Path $zipDir)) {
        New-Item -ItemType Directory -Path $zipDir -Force | Out-Null
    }
    
    # 使用 PowerShell 的 Compress-Archive 压缩
    try {
        Compress-Archive -Path "$BuildDir\*" -DestinationPath $zipFile -Force
        Write-Info "压缩完成: $zipFile"
        return $zipFile
    } catch {
        # 如果 Compress-Archive 失败，尝试使用 zip 命令（如果可用）
        if (Get-Command zip -ErrorAction SilentlyContinue) {
            try {
                Push-Location $BuildDir
                zip -r $zipFile . | Out-Null
                Pop-Location
                Write-Info "压缩完成: $zipFile"
                return $zipFile
            } catch {
                Write-Error "压缩失败: $_.Exception.Message"
                exit 1
            }
        } else {
            Write-Error "压缩失败: $_.Exception.Message"
            Write-Error "请确保 PowerShell 的 Compress-Archive 功能可用，或安装 zip 工具"
            exit 1
        }
    }
}

# 删除构建目录
function Remove-BuildDirectory {
    param([string]$BuildDir)
    
    if (-not (Test-Path $BuildDir)) {
        Write-Warn "构建目录不存在，跳过删除: $BuildDir"
        return
    }
    
    Write-Info "正在删除构建目录: $BuildDir"
    try {
        Remove-Item -Path $BuildDir -Recurse -Force
        if (Test-Path $BuildDir) {
            Write-Error "构建目录删除失败: $BuildDir"
            exit 1
        } else {
            Write-Info "构建目录已删除"
        }
    } catch {
        Write-Error "构建目录删除失败: $_.Exception.Message"
        exit 1
    }
}

# 主函数
function Main {
    param([string[]]$Arguments)
    
    # 解析参数
    $cleanBuildDir = $false
    $targetAgent = ""
    $outputPath = ""
    $version = "v1.0.0"  # 默认版本号为 v1.0.0
    
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
                    Write-Error "--output 选项需要指定路径"
                    Write-Error "使用 '$PSCommandPath -h' 或 '$PSCommandPath --help' 查看详细使用说明"
                    exit 1
                }
                $outputPath = $Arguments[++$i]
            }
            { $_ -in '--clean', '--remove' } {
                $cleanBuildDir = $true
            }
            default {
                # 第一个非选项参数作为 agent 名称
                if ([string]::IsNullOrEmpty($targetAgent)) {
                    $targetAgent = $arg
                } else {
                    Write-Error "未知参数: $arg"
                    Write-Error "使用 '$PSCommandPath -h' 或 '$PSCommandPath --help' 查看详细使用说明"
                    exit 1
                }
            }
        }
    }
    
    # 如果未提供 agent 名称，使用默认值
    if ([string]::IsNullOrEmpty($targetAgent)) {
        $TARGET_AGENT = "claude"
    } else {
        $TARGET_AGENT = $targetAgent
    }
    
    # 如果目录名不以点号开头，则添加点号
    if (-not $TARGET_AGENT.StartsWith(".")) {
        $TARGET_AGENT = ".$TARGET_AGENT"
    }
    
    Write-Host "=========================================="
    Write-Host "  OmniSpec 构建脚本"
    Write-Host "=========================================="
    Write-Host ""
    
    # 验证版本号格式
    if (-not (Test-Version -Version $version)) {
        exit 1
    }
    
    # 获取安装脚本路径
    $INSTALL_SCRIPT = Get-InstallScript
    
    # 检查安装脚本是否存在
    Test-InstallScript -InstallScript $INSTALL_SCRIPT
    
    # 获取时间戳
    $TIMESTAMP = Get-Timestamp
    Write-Info "时间戳: $TIMESTAMP"
    Write-Info "版本号: $version"
    
    # 生成统一的构建名称（用于文件夹和zip文件名）
    $BUILD_NAME = Get-BuildName -AgentName $TARGET_AGENT -Timestamp $TIMESTAMP -Version $version
    Write-Info "构建名称: $BUILD_NAME"
    
    # 获取版本号（与构建名称相同）
    $VERSION = $BUILD_NAME
    Write-Info "版本号: $VERSION"
    Write-Host ""
    
    # 生成构建时间（统一生成，多点使用）
    $BUILD_DATE = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Info "构建时间: $BUILD_DATE"
    Write-Host ""
    
    # 显示输出路径信息
    if (-not [string]::IsNullOrEmpty($outputPath)) {
        $absOutputPath = (Resolve-Path -Path $outputPath -ErrorAction Stop).Path
        Write-Info "输出路径: $absOutputPath"
        Write-Host ""
    }
    
    # 创建构建目录（使用统一的构建名称）
    $BUILD_DIR = New-BuildDirectory -BuildName $BUILD_NAME -OutputPath $outputPath
    Write-Host ""
    
    # 运行安装脚本
    Invoke-InstallScript -InstallScript $INSTALL_SCRIPT -BuildDir $BUILD_DIR -TargetAgent $TARGET_AGENT
    Write-Host ""
    
    # 复制版本发布说明文件到 .specify 文件夹
    Copy-ReleaseNotes -BuildDir $BUILD_DIR
    Write-Host ""
    
    # 生成安装版本开发视图文件
    Write-SpecFileList -BuildDir $BUILD_DIR -AgentName $TARGET_AGENT -Version $VERSION -BuildDate $BUILD_DATE
    Write-Host ""
    
    # 压缩目录（使用统一的构建名称）
    $ZIP_FILE = New-ZipFile -BuildDir $BUILD_DIR -BuildName $BUILD_NAME -OutputPath $outputPath
    Write-Host ""
    
    # 根据参数决定是否删除构建目录
    if ($cleanBuildDir) {
        # 删除构建目录
        Remove-BuildDirectory -BuildDir $BUILD_DIR
        Write-Host ""
    } else {
        Write-Info "构建目录已保留: $BUILD_DIR"
        Write-Host ""
    }
    
    Write-Host "=========================================="
    Write-Info "构建完成！"
    Write-Host "=========================================="
    Write-Host ""
    Write-Info "ZIP 文件: $ZIP_FILE"
    if (-not $cleanBuildDir) {
        Write-Info "构建目录: $BUILD_DIR"
    }
    Write-Host ""
}

# 执行主函数
Main -Arguments $args


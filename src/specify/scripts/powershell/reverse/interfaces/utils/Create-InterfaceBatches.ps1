#!/usr/bin/env pwsh
# 创建接口批次文件工具 (PowerShell版本)
# 调用Python脚本创建接口批次文件
#
# 使用方法:
#   .\Create-InterfaceBatches.ps1 -RepoRoot <repo_root> [-Force]
#

param(
    [Parameter(Mandatory=$true)]
    [string]$RepoRoot,

    [Parameter(Mandatory=$false)]
    [switch]$Force,

    [switch]$Help
)

# 显示帮助信息
function Show-Help {
    @"
使用方法:
    .\Create-InterfaceBatches.ps1 -RepoRoot <repo_root> [-Force]

参数:
    -RepoRoot: 仓库根目录路径
    -Force: 强制重新生成批次文件，即使已存在
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

# 获取脚本目录
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$pythonScript = Join-Path -Path $scriptDir -ChildPath "..\..\..\..\..\python\reverse_interfaces\create_interface_batches.py" | Resolve-Path

# 检查Python脚本是否存在
if (-not (Test-Path -Path $pythonScript -PathType Leaf)) {
    Write-Error "错误: Python脚本不存在 $pythonScript"
    exit 1
}

# 执行Python脚本
try {
    $arguments = @($RepoRoot)
    if ($Force) {
        $arguments += "--force"
    }
    
    $output = & python $pythonScript $arguments
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Python脚本执行失败: $output"
        exit 1
    }
    Write-Output $output
} catch {
    Write-Error "执行过程中发生错误: $_"
    exit 1
}


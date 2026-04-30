# 生成接口清单脚本
# 用途: 收集所有已生成的接口详情文档信息，根据模板生成汇总接口清单文档

param(
    [Parameter(Mandatory=$true)]
    [string]$RepoRoot,

    [switch]$Help
)

# 显示使用方法
function Show-Usage {
    Write-Host "用法: .\generate_interface_inventory.ps1 -RepoRoot <仓库根目录>"
    Write-Host "示例: .\generate_interface_inventory.ps1 -RepoRoot C:\path\to\project"
}

# 日志函数
function Write-LogInfo {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Green
}

function Write-LogWarn {
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Write-LogError {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# 检查帮助参数
if ($Help) {
    Show-Usage
    exit 0
}

# 检查目录是否存在
if (-not (Test-Path $RepoRoot)) {
    Write-LogError "仓库根目录不存在: $RepoRoot"
    exit 1
}

# 加载公共函数
$CommonScript = Join-Path $PSScriptRoot "..\..\..\..\powershell\common.ps1"
if (Test-Path $CommonScript) {
    . $CommonScript
} else {
    Write-LogError "无法加载公共函数脚本: $CommonScript"
    exit 1
}

# 定义路径
# 使用 Find-TemplateFile 查找模板文件（支持按项目查找）
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$OmniSpecRoot = (Resolve-Path (Join-Path $ScriptDir "..\..\..\..\..\..")).Path
$TemplateFile = Find-TemplateFile -TemplateFilename "reverse-interface-inventory-template.md" -RepoRoot $RepoRoot -OmniSpecRoot $OmniSpecRoot
if (-not $TemplateFile -or -not (Test-Path $TemplateFile)) {
    Write-LogError "接口清单模板文件未找到"
    exit 1
}

$OutputDir = Join-Path $RepoRoot "omni-doc\interfaces"
$InventoryFile = Join-Path $OutputDir "接口清单.md"
$InterfaceListFile = Join-Path $RepoRoot ".cache\reverse\interfaces\interface-list.json"

# 检查输出目录是否存在，不存在则创建
if (-not (Test-Path $OutputDir)) {
    Write-LogInfo "创建输出目录: $OutputDir"
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

Write-LogInfo "开始生成接口清单..."

# 质量门禁：生成接口清单前先二次校验接口文档命名与 frontmatter
Write-LogInfo "执行接口文档命名质量门禁..."
$ValidatorScript = Join-Path $RepoRoot "claude\skills\reverse-interfaces\references\scripts\validate_and_fix_interface_doc_filenames.py"
python3 $ValidatorScript $RepoRoot
if ($LASTEXITCODE -ne 0) {
    Write-LogError "接口文档质量门禁未通过，已停止生成接口清单（退出码: $LASTEXITCODE）"
    exit 1
}

# 获取生成时间
$GeneratedAt = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

# 初始化统计数据
$TotalCount = 0
$TypeStatistics = @()

# 如果接口列表文件存在，则从中获取统计数据
if (Test-Path $InterfaceListFile) {
    Write-LogInfo "从接口列表文件获取统计数据: $InterfaceListFile"

    try {
        $InterfaceData = Get-Content $InterfaceListFile | ConvertFrom-Json

        # 获取接口总数
        if ($InterfaceData.PSObject.Properties.Name -contains "interfaces") {
            $TotalCount = $InterfaceData.interfaces.Count

            # 获取接口类型统计
            if ($TotalCount -gt 0) {
                $GroupedInterfaces = $InterfaceData.interfaces | Group-Object interface_type
                foreach ($Group in $GroupedInterfaces) {
                    $TypeName = $Group.Name
                    $Count = $Group.Count
                    $TypeStatistics += "- **$TypeName接口**: $Count 个"
                }
            }
        }
    } catch {
        Write-LogWarn "解析接口列表文件失败: $_"
    }
} else {
    Write-LogWarn "接口列表文件不存在: $InterfaceListFile"
    # 通过扫描output目录下的接口文件来统计
    $InterfaceFiles = Get-ChildItem -Path $OutputDir -Filter "*.md" -Exclude "接口清单.md" -ErrorAction SilentlyContinue
    $TotalCount = $InterfaceFiles.Count
}

# 收集接口列表信息
$InterfacesTable = ""

# 查找所有接口详情文档（排除接口清单本身）
$InterfaceDetailFiles = Get-ChildItem -Path $OutputDir -Filter "*.md" -Exclude "接口清单.md" | Sort-Object Name

if ($InterfaceDetailFiles) {
    foreach ($File in $InterfaceDetailFiles) {
        # 从文件名提取接口ID和接口名称
        $Filename = [System.IO.Path]::GetFileNameWithoutExtension($File.Name)

        # 尝试从文件内容提取接口信息
        if (Test-Path $File.FullName) {
            try {
                $FileContent = Get-Content $File.FullName -Encoding UTF8

                # 提取接口ID
                $InterfaceIdLine = $FileContent | Where-Object { $_ -match '^\- \*\*接口ID\*\*: ' } | Select-Object -First 1
                if ($InterfaceIdLine) {
                    $InterfaceId = $InterfaceIdLine -replace '^- \*\*接口ID\*\*: ', ''
                } else {
                    $InterfaceId = "N/A"
                }

                # 提取接口名称
                $InterfaceNameLine = $FileContent | Where-Object { $_ -match '^\- \*\*接口名称\*\*: ' } | Select-Object -First 1
                if ($InterfaceNameLine) {
                    $InterfaceName = $InterfaceNameLine -replace '^- \*\*接口名称\*\*: ', ''
                } else {
                    $InterfaceName = $Filename
                }

                # 提取接口类型
                $InterfaceTypeLine = $FileContent | Where-Object { $_ -match '^\- \*\*接口类型\*\*: ' } | Select-Object -First 1
                if ($InterfaceTypeLine) {
                    $InterfaceType = $InterfaceTypeLine -replace '^- \*\*接口类型\*\*: ', ''
                } else {
                    $InterfaceType = "N/A"
                }

                # 提取所属文件
                $SourceFileLine = $FileContent | Where-Object { $_ -match '^\- \*\*所属文件\*\*: ' } | Select-Object -First 1
                if ($SourceFileLine) {
                    $SourceFile = $SourceFileLine -replace '^- \*\*所属文件\*\*: ', ''
                } else {
                    $SourceFile = "N/A"
                }

                # 如果从文件内容无法提取到有效ID，则使用文件名
                if ($InterfaceId -eq "N/A" -or -not $InterfaceId) {
                    $InterfaceId = $Filename
                }

                # 生成相对路径用于链接
                $RelativeFile = "./$($File.Name)"

                # 提取业务名称（如果存在）
                $BusinessNameLine = $FileContent | Where-Object { $_ -match '^\- \*\*业务名称\*\*: ' } | Select-Object -First 1
                if ($BusinessNameLine) {
                    $BusinessName = $BusinessNameLine -replace '^- \*\*业务名称\*\*: ', ''
                } else {
                    $BusinessName = $InterfaceName
                }

                # 提取业务领域（如果存在）
                $BusinessDomainLine = $FileContent | Where-Object { $_ -match '^\- \*\*业务领域\*\*: ' } | Select-Object -First 1
                if ($BusinessDomainLine) {
                    $BusinessDomain = $BusinessDomainLine -replace '^- \*\*业务领域\*\*: ', ''
                } else {
                    $BusinessDomain = "N/A"
                }

                # 添加到表格
                $InterfacesTable += "| $InterfaceId | $BusinessName | $InterfaceType | $BusinessDomain | [$BusinessName]($RelativeFile) |`n"
            } catch {
                Write-LogWarn "读取文件失败 $($File.FullName): $_"
            }
        }
    }
}

# 读取模板内容
try {
    $TemplateContent = Get-Content $TemplateFile -Raw -Encoding UTF8
} catch {
    Write-LogError "读取模板文件失败: $_"
    exit 1
}

# 替换模板变量
$FinalContent = $TemplateContent
$FinalContent = $FinalContent -replace '\{\{generated_at\}\}', $GeneratedAt
$FinalContent = $FinalContent -replace '\{\{total_count\}\}', $TotalCount

# 处理类型统计部分
if ($TypeStatistics.Count -gt 0) {
    $TypeStatsContent = ($TypeStatistics -join "`n")

    # 替换类型统计部分
    $FinalContent = [regex]::Replace($FinalContent, '\{\{#type_statistics\}\}.*?\{\{/type_statistics\}\}', $TypeStatsContent, [System.Text.RegularExpressions.RegexOptions]::Singleline)
} else {
    # 如果没有类型统计，删除占位符
    $FinalContent = [regex]::Replace($FinalContent, '\{\{#type_statistics\}\}.*?\{\{/type_statistics\}\}', '', [System.Text.RegularExpressions.RegexOptions]::Singleline)
}

# 处理接口列表部分
if ($InterfacesTable) {
    # 移除最后的换行符
    $InterfacesTable = $InterfacesTable.TrimEnd("`n")

    # 替换接口列表部分
    $FinalContent = [regex]::Replace($FinalContent, '\{\{#interfaces\}\}.*?\{\{/interfaces\}\}', $InterfacesTable, [System.Text.RegularExpressions.RegexOptions]::Singleline)
} else {
    # 如果没有接口列表，删除占位符
    $FinalContent = [regex]::Replace($FinalContent, '\{\{#interfaces\}\}.*?\{\{/interfaces\}\}', '', [System.Text.RegularExpressions.RegexOptions]::Singleline)
}

# 写入重试机制
$MaxRetries = 3
$RetryCount = 0
$Success = $false

while ($RetryCount -lt $MaxRetries -and -not $Success) {
    $RetryCount++
    Write-LogInfo "尝试写入接口清单文件 (第 $RetryCount/$MaxRetries 次)..."

    try {
        # 尝试写入文件
        $FinalContent | Out-File -FilePath $InventoryFile -Encoding UTF8 -Force
        $Success = $true
        Write-LogInfo "接口清单文件生成成功: $InventoryFile"
    } catch {
        Write-LogWarn "写入失败，$([Math]::Pow(2, $RetryCount))秒后重试..."
        Start-Sleep -Seconds ([Math]::Pow(2, $RetryCount))
    }
}

if (-not $Success) {
    Write-LogError "写入接口清单文件失败，已重试 $MaxRetries 次"
    exit 1
}

# 验证生成的文件
if (Test-Path $InventoryFile) {
    $GeneratedSize = (Get-Item $InventoryFile).Length
    if ($GeneratedSize -gt 0) {
        Write-LogInfo "接口清单生成完成，文件大小: $GeneratedSize 字节"
        Write-Host "接口清单已生成到: $InventoryFile"
        exit 0
    } else {
        Write-LogError "生成的接口清单文件为空"
        exit 1
    }
} else {
    Write-LogError "接口清单文件未找到: $InventoryFile"
    exit 1
}
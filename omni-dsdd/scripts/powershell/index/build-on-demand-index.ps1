#!/usr/bin/env pwsh
$ErrorActionPreference = 'Stop'

<#
.SYNOPSIS
构建 on-demand 关系索引：
- branch-function.json（分支 -> 功能标识列表）
- function-interface.json（功能 -> 接口标识列表）
- branch-interface.json（分支 -> 接口标识列表）

.DESCRIPTION
数据源：
- omni-doc/on-demand/on-demand-existing-function-analysis-*.md（主汇总文档）
- omni-doc/on-demand/functions/*.md（功能文档存在性校验）

行为：
- 全量重建
- function_key 仅允许 [a-z0-9_-]+
- 仅收录存在功能文档的 function_key
- targets 去重 + 字典序排序
- 原子写入：写入 *.tmp 后 Move-Item 覆盖

.PARAMETER RepoRoot
仓库根目录（绝对或相对路径均可）

.PARAMETER DryRun
仅打印统计信息，不落盘写文件

.PARAMETER Help
显示帮助
#>

param()

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $ScriptDir "../../common.ps1")

function Log-Info([string]$Msg) { Write-Host "[build-on-demand-index] INFO: $Msg" }
function Log-Warn([string]$Msg) { Write-Warning "[build-on-demand-index] WARN: $Msg" }
function Die([string]$Msg) { Write-Error "[build-on-demand-index] ERROR: $Msg"; exit 1 }

function Print-Help {
@"
用法:
  build-on-demand-index.ps1 --repo-root <REPO_ROOT> [--dry-run]

参数:
  --repo-root <path>   仓库根目录（绝对路径或相对路径均可）
  --dry-run            仅打印将写入的目标路径与统计信息，不落盘写文件
  --help               显示帮助

产物:
  <REPO_ROOT>/omni-doc/on-demand/relations/branch-function.json
  <REPO_ROOT>/omni-doc/on-demand/relations/function-interface.json
  <REPO_ROOT>/omni-doc/on-demand/relations/branch-interface.json

说明:
  - 全量重建：扫描所有主汇总文档 on-demand/on-demand-existing-function-analysis-*.md
  - 仅收录存在功能文档的 function_key：omni-doc/on-demand/functions/<function_key>.md
  - function_key 仅允许 [a-z0-9_-]+
  - 原子写入：先写 *.tmp，校验 JSON 后覆盖目标文件
"@ | Write-Host
}

function Resolve-RepoRoot([string]$Path) {
  if (-not $Path) { Die "必须提供 --repo-root" }
  return (Resolve-Path $Path).Path
}

function Parse-Args([string[]]$Argv) {
  $result = @{
    RepoRoot = $null
    DryRun   = $false
    Help     = $false
  }

  for ($i = 0; $i -lt $Argv.Count; $i++) {
    $a = $Argv[$i]
    if ($a -eq '--help' -or $a -eq '-h') {
      $result.Help = $true
      continue
    }
    if ($a -eq '--dry-run') {
      $result.DryRun = $true
      continue
    }
    if ($a -like '--repo-root=*') {
      $result.RepoRoot = ($a -split '=', 2)[1]
      continue
    }
    if ($a -eq '--repo-root') {
      if ($i + 1 -ge $Argv.Count) { Die "--repo-root 需要一个参数" }
      $result.RepoRoot = $Argv[$i + 1]
      $i++
      continue
    }
    # 兼容 PowerShell 风格参数（可选）
    if ($a -like '-RepoRoot=*') {
      $result.RepoRoot = ($a -split '=', 2)[1]
      continue
    }
    if ($a -eq '-RepoRoot') {
      if ($i + 1 -ge $Argv.Count) { Die "-RepoRoot 需要一个参数" }
      $result.RepoRoot = $Argv[$i + 1]
      $i++
      continue
    }
    if ($a -eq '-DryRun') {
      $result.DryRun = $true
      continue
    }

    Die "未知参数：$a（使用 --help 查看用法）"
  }

  return $result
}

function Extract-BranchName([string]$DocPath) {
  $bn = Split-Path -Leaf $DocPath
  if ($bn -match '^on-demand-existing-function-analysis-(.+)\.md$') {
    return $Matches[1]
  }
  return $null
}

function Validate-FunctionKey([string]$Key) {
  return ($Key -match '^[a-z0-9_-]+$')
}

function Validate-InterfaceKey([string]$Key) {
  return ($Key -match '^[a-z0-9_-]+$')
}

function Extract-InterfaceKeysFromFunctionDoc([string]$DocPath) {
  $text = Get-Content -Path $DocPath -Raw -ErrorAction Stop
  $matches = [regex]::Matches($text, '(?:\.\./interfaces/|on-demand/interfaces/)([a-z0-9_-]+)\.md')
  $set = New-Object System.Collections.Generic.HashSet[string]
  foreach ($m in $matches) {
    if ($m.Groups.Count -gt 1) { [void]$set.Add($m.Groups[1].Value) }
  }
  return ($set.ToArray() | Sort-Object)
}

function Extract-FunctionKeysFromMainDoc([string[]]$Lines) {
  # 解析 “2.1 功能清单” 表格的 “功能标识” 列
  $start = $null
  for ($i = 0; $i -lt $Lines.Count; $i++) {
    if ($Lines[$i] -like '*2.1*' -and $Lines[$i] -like '*功能清单*') {
      $start = $i
      break
    }
  }

  if ($null -eq $start) { return @() }

  $headerIdx = $null
  for ($j = $start + 1; $j -lt $Lines.Count; $j++) {
    $l = $Lines[$j].TrimStart()
    if ($l.StartsWith('|')) { $headerIdx = $j; break }
    if ($l -match '^\s*#{1,6}\s+') { break }
  }
  if ($null -eq $headerIdx) { return @() }
  if ($headerIdx + 1 -ge $Lines.Count) { return @() }

  $header = ($Lines[$headerIdx].Trim().Trim('|').Split('|') | ForEach-Object { $_.Trim() })
  $sep = $Lines[$headerIdx + 1].Trim()
  if (-not ($sep.TrimStart().StartsWith('|') -and $sep -match '---')) { return @() }

  $col = [Array]::IndexOf($header, '功能标识')
  if ($col -lt 0) { return @() }

  $keys = New-Object System.Collections.Generic.List[string]
  for ($k = $headerIdx + 2; $k -lt $Lines.Count; $k++) {
    $line = $Lines[$k].Trim()
    if (-not $line.StartsWith('|')) { break }
    $cols = ($line.Trim('|').Split('|') | ForEach-Object { $_.Trim() })
    if ($col -lt $cols.Count) {
      $v = $cols[$col].Trim()
      if ($v) { [void]$keys.Add($v) }
    }
  }
  return $keys.ToArray()
}

function Build-Pairs([string]$RepoRoot) {
  $sk = Join-Path $RepoRoot "omni-doc"
  if (-not (Test-Path $sk)) { Die "目录不存在：$sk" }

  $functionsDir = Join-Path $sk "on-demand/functions"
  if (-not (Test-Path $functionsDir)) { Log-Warn "功能文档目录不存在：$functionsDir（将导致 targets 为空）" }

  $mainDocs = Get-ChildItem -Path (Join-Path $sk "on-demand") -Filter "on-demand-existing-function-analysis-*.md" -File -ErrorAction SilentlyContinue
  if (-not $mainDocs -or $mainDocs.Count -eq 0) {
    Log-Warn "未找到主汇总文档：$sk/on-demand/on-demand-existing-function-analysis-*.md"
    return @()
  }

  $pairs = New-Object System.Collections.Generic.List[object]
  foreach ($doc in $mainDocs) {
    $lines = Get-Content -Path $doc.FullName -ErrorAction Stop
    $branch = Extract-BranchName -DocPath $doc.FullName
    if (-not $branch) {
      Log-Warn "无法提取 branch_name，跳过：$($doc.FullName)"
      continue
    }

    $keys = Extract-FunctionKeysFromMainDoc -Lines $lines
    foreach ($raw in $keys) {
      $key = $raw.Trim()
      if (-not $key) { continue }

      if (-not (Validate-FunctionKey $key)) {
        Log-Warn "function_key 非法（仅允许 [a-z0-9_-]+），跳过：branch=$branch key=$key doc=$($doc.Name)"
        continue
      }

      $fdoc = Join-Path $functionsDir "$key.md"
      if (-not (Test-Path $fdoc -PathType Leaf)) {
        Log-Warn "功能文档不存在，跳过：branch=$branch key=$key expected=$fdoc"
        continue
      }

      $pairs.Add([PSCustomObject]@{ rid = $branch; key = $key }) | Out-Null
    }
  }

  return $pairs.ToArray()
}

function Write-RelationsJsonAtomically([object[]]$Pairs, [string]$OutJson) {
  $outDir = Split-Path -Parent $OutJson
  if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir -Force | Out-Null }

  $tmp = "$OutJson.tmp"

  $map = @{}
  foreach ($p in $Pairs) {
    if (-not $map.ContainsKey($p.rid)) { $map[$p.rid] = New-Object System.Collections.Generic.HashSet[string] }
    [void]$map[$p.rid].Add($p.key)
  }

  $relations = @()
  foreach ($rid in ($map.Keys | Sort-Object)) {
    $targets = $map[$rid].ToArray() | Sort-Object
    $relations += [PSCustomObject]@{ source = $rid; targets = $targets }
  }

  $json = $relations | ConvertTo-Json -Depth 10
  # ConvertTo-Json 默认不带结尾换行，这里补一个，保持 diff 稳定
  [System.IO.File]::WriteAllText($tmp, $json + "`n", [System.Text.Encoding]::UTF8)

  # parse check
  $null = Get-Content $tmp -Raw | ConvertFrom-Json

  Move-Item -Path $tmp -Destination $OutJson -Force
}

function Build-FunctionInterfacePairs([string]$RepoRoot) {
  $functionsDir = Join-Path $RepoRoot "omni-doc/on-demand/functions"
  $interfacesDir = Join-Path $RepoRoot "omni-doc/on-demand/interfaces"

  if (-not (Test-Path $functionsDir)) {
    Log-Warn "功能文档目录不存在：$functionsDir（将导致 function-interface 为空）"
    return @()
  }
  if (-not (Test-Path $interfacesDir)) {
    Log-Warn "接口文档目录不存在：$interfacesDir（将导致 function-interface 为空）"
  }

  $pairs = New-Object System.Collections.Generic.List[object]
  $functionDocs = Get-ChildItem -Path $functionsDir -Filter "*.md" -File -ErrorAction SilentlyContinue

  foreach ($doc in $functionDocs) {
    $fkey = [System.IO.Path]::GetFileNameWithoutExtension($doc.Name)
    if (-not (Validate-FunctionKey $fkey)) {
      Log-Warn "功能文档文件名非法，跳过：$($doc.FullName)"
      continue
    }

    $interfaceKeys = Extract-InterfaceKeysFromFunctionDoc -DocPath $doc.FullName
    foreach ($ikey in $interfaceKeys) {
      if (-not (Validate-InterfaceKey $ikey)) {
        Log-Warn "interface_key 非法（仅允许 [a-z0-9_-]+），跳过：fkey=$fkey ikey=$ikey"
        continue
      }

      $idoc = Join-Path $interfacesDir "$ikey.md"
      if (-not (Test-Path $idoc -PathType Leaf)) {
        Log-Warn "接口文档不存在，跳过：fkey=$fkey ikey=$ikey expected=$idoc"
        continue
      }

      $pairs.Add([PSCustomObject]@{ source = $fkey; targets = $ikey }) | Out-Null
    }
  }

  return $pairs.ToArray()
}

function Write-RequirementInterfaceJsonAtomically([object[]]$RequirementFunctionPairs, [object[]]$FunctionInterfacePairs, [string]$OutJson) {
  $outDir = Split-Path -Parent $OutJson
  if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir -Force | Out-Null }
  $tmp = "$OutJson.tmp"

  $reqToFunctions = @{}
  foreach ($p in $RequirementFunctionPairs) {
    if (-not $reqToFunctions.ContainsKey($p.source)) {
      $reqToFunctions[$p.source] = New-Object System.Collections.Generic.HashSet[string]
    }
    [void]$reqToFunctions[$p.source].Add($p.targets)
  }

  $funcToInterfaces = @{}
  foreach ($p in $FunctionInterfacePairs) {
    if (-not $funcToInterfaces.ContainsKey($p.source)) {
      $funcToInterfaces[$p.source] = New-Object System.Collections.Generic.HashSet[string]
    }
    [void]$funcToInterfaces[$p.source].Add($p.targets)
  }

  $relations = @()
  foreach ($rid in ($reqToFunctions.Keys | Sort-Object)) {
    $interfaces = New-Object System.Collections.Generic.HashSet[string]
    foreach ($fkey in $reqToFunctions[$rid]) {
      if ($funcToInterfaces.ContainsKey($fkey)) {
        foreach ($ikey in $funcToInterfaces[$fkey]) { [void]$interfaces.Add($ikey) }
      }
    }
    $relations += [PSCustomObject]@{
      source  = $rid
      targets = ($interfaces.ToArray() | Sort-Object)
    }
  }

  $json = $relations | ConvertTo-Json -Depth 10
  [System.IO.File]::WriteAllText($tmp, $json + "`n", [System.Text.Encoding]::UTF8)
  $null = Get-Content $tmp -Raw | ConvertFrom-Json
  Move-Item -Path $tmp -Destination $OutJson -Force
}

 $parsed = Parse-Args $args

if ($parsed.Help) {
  Print-Help
  exit 0
}

if (-not $parsed.RepoRoot) {
  Die "必须提供 --repo-root（或 -RepoRoot）"
}

$RepoRoot = Resolve-RepoRoot $parsed.RepoRoot
$bfJson = Join-Path $RepoRoot "omni-doc/on-demand/relations/branch-function.json"
$fiJson = Join-Path $RepoRoot "omni-doc/on-demand/relations/function-interface.json"
$biJson = Join-Path $RepoRoot "omni-doc/on-demand/relations/branch-interface.json"
$legacyRfJson = Join-Path $RepoRoot "omni-doc/on-demand/relations/requirement-function.json"
$legacyRiJson = Join-Path $RepoRoot "omni-doc/on-demand/relations/requirement-interface.json"

Log-Info "开始构建关系文件（全量重建）"
Log-Info "REPO_ROOT=$RepoRoot"

$pairs = Build-Pairs $RepoRoot
$fiPairs = Build-FunctionInterfacePairs $RepoRoot
Log-Info ("收集到 (branch_name, function_key) 记录数：{0}" -f $pairs.Count)
Log-Info ("收集到 (function_key, interface_key) 记录数：{0}" -f $fiPairs.Count)

if ($parsed.DryRun) {
  Log-Info "--dry-run：不落盘写入"
  Log-Info "目标文件：$bfJson"
  Log-Info "目标文件：$fiJson"
  Log-Info "目标文件：$biJson"
  Log-Info "兼容文件：$legacyRfJson"
  Log-Info "兼容文件：$legacyRiJson"
  exit 0
}

Write-RelationsJsonAtomically -Pairs $pairs -OutJson $bfJson
Write-RelationsJsonAtomically -Pairs $fiPairs -OutJson $fiJson
Write-RequirementInterfaceJsonAtomically -RequirementFunctionPairs $pairs -FunctionInterfacePairs $fiPairs -OutJson $biJson
Copy-Item -Path $bfJson -Destination $legacyRfJson -Force
Copy-Item -Path $biJson -Destination $legacyRiJson -Force
Log-Info "写入完成：$bfJson"
Log-Info "写入完成：$fiJson"
Log-Info "写入完成：$biJson"
Log-Info "兼容写入完成：$legacyRfJson"
Log-Info "兼容写入完成：$legacyRiJson"



[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ArgsList
)

# 初始化 reverse-on-demand harness（阶段2四项约束骨架）
# 本脚本为 python harness (reverse_on_demand_harness.py init) 的转发壳，骨架生成逻辑均在 python 端。
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$HarnessPy = Join-Path $ScriptDir "..\python\reverse_on_demand_harness.py"

if (-not (Get-Command python3 -ErrorAction SilentlyContinue)) {
    Write-Error "ERROR: python3 is required"
    exit 1
}

if (-not $ArgsList -or $ArgsList.Count -lt 1) {
    Write-Error "用法: Reverse-On-Demand-InitHarness.ps1 --working-dir <WORKING_DIR> --feature-dir <FEATURE_DIR> [--repo-root <REPO_ROOT>]"
    exit 1
}

& python3 $HarnessPy init @ArgsList
exit $LASTEXITCODE

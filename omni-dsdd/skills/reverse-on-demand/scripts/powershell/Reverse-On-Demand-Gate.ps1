[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ArgsList
)

# reverse-on-demand 阶段2 Harness 门禁（全仓检索 / 调用链深度 / 配置解析 / 多语言覆盖）
# 本脚本为 python harness (reverse_on_demand_harness.py gate) 的转发壳，校验逻辑均在 python 端。
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$HarnessPy = Join-Path $ScriptDir "..\python\reverse_on_demand_harness.py"

if (-not (Get-Command python3 -ErrorAction SilentlyContinue)) {
    Write-Error "ERROR: python3 is required"
    exit 1
}

if (-not $ArgsList -or $ArgsList.Count -lt 1) {
    Write-Error "用法: Reverse-On-Demand-Gate.ps1 --working-dir <WORKING_DIR> --feature-dir <FEATURE_DIR> [--repo-root <REPO_ROOT>] [--step <stage2|all>] [--record]"
    exit 1
}

& python3 $HarnessPy gate @ArgsList
exit $LASTEXITCODE

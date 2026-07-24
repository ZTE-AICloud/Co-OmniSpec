[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ArgsList
)

# 阶段2波及检索全量 Harness 校验（= Gate --step all --record），含多语言覆盖校验
# 本脚本为 Gate.ps1 的转发壳，校验逻辑均在 python 端。
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$GateScript = Join-Path $ScriptDir "Reverse-On-Demand-Gate.ps1"

if (-not $ArgsList -or $ArgsList.Count -lt 1) {
    Write-Error "用法: Verify-Reverse-On-Demand-Stage2.ps1 --working-dir <WORKING_DIR> --feature-dir <FEATURE_DIR> [--repo-root <REPO_ROOT>]"
    exit 1
}

& $GateScript @ArgsList "--step" "all" "--record"
exit $LASTEXITCODE

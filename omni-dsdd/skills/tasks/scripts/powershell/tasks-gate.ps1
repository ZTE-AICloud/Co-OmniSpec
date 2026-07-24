#!/usr/bin/env pwsh
# Tasks 阶段门禁脚本 (Windows PowerShell)

param(
    [Parameter(Mandatory=$true)]
    [string]$FeatureDir,

    [Parameter(Mandatory=$false)]
    [ValidateSet("init", "context", "requirements", "scenarios", "quality", "all")]
    [string]$Step = "all",

    [switch]$Json,
    [switch]$Record,
    [switch]$EnableE2e
)

$ErrorActionPreference = 'Stop'

# 获取脚本目录
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$HarnessScript = Join-Path $ScriptDir "..\python\tasks_harness.py"

# 检查 harness 是否存在
if (-not (Test-Path $HarnessScript)) {
    Write-Error "tasks_harness.py not found at $HarnessScript"
    exit 1
}

# 构建参数
$Args = @(
    "gate",
    "--feature-dir", $FeatureDir,
    "--step", $Step
)

if ($Json) {
    $Args += "--json"
}

if ($Record) {
    $Args += "--record"
}

if ($EnableE2e) {
    $Args += "--enable-e2e"
}

# 调用 Python harness
& python3 $HarnessScript @Args
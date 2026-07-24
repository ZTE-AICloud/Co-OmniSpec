#!/usr/bin/env pwsh
# spec-impact-analyze 私域知识检索门禁（skills/spec-impact-analyze 专用）
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'SpecImpact-HarnessCommon.ps1')
Invoke-ImpactGate -GateArgs (@('gate') + $args)

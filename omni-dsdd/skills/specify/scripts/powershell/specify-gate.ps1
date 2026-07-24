#!/usr/bin/env pwsh
# specify 分步/全量 Harness 门禁（skills/specify 专用）
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Specify-HarnessCommon.ps1')
Invoke-SpecifyHarness -HarnessArgs (@('gate') + $args)

#!/usr/bin/env pwsh
# design 分步/全量 Harness 门禁（skills/design 专用）
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Design-HarnessCommon.ps1')
Invoke-DesignHarness -HarnessArgs (@('gate') + $args)

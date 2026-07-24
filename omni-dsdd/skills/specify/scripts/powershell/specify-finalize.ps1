#!/usr/bin/env pwsh
# specify 完成后同步 omnispec-state（skills/specify 专用）
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Specify-HarnessCommon.ps1')
Invoke-SpecifyHarness -HarnessArgs (@('finalize') + $args)

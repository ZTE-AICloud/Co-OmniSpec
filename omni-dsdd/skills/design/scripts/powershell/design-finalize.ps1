#!/usr/bin/env pwsh
# design 完成后同步 omnispec-state（skills/design 专用）
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Design-HarnessCommon.ps1')
Invoke-DesignHarness -HarnessArgs (@('finalize') + $args)

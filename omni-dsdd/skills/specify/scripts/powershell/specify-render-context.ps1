#!/usr/bin/env pwsh
# 从 context.payload.json 渲染 context.md（skills/specify 专用）
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Specify-HarnessCommon.ps1')
Invoke-SpecifyHarness -HarnessArgs (@('render-context') + $args)

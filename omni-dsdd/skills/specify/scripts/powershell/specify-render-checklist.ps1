#!/usr/bin/env pwsh
# 从 requirements-template.md 渲染检查清单（skills/specify 专用）
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Specify-HarnessCommon.ps1')
Invoke-SpecifyHarness -HarnessArgs (@('render-checklist') + $args)

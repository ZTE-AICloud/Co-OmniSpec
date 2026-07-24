#!/usr/bin/env pwsh
# 从 spec-template.md 渲染 spec.md 骨架（skills/specify 专用）
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Specify-HarnessCommon.ps1')
Invoke-SpecifyHarness -HarnessArgs (@('render-spec') + $args)

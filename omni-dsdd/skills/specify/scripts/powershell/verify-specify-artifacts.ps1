#!/usr/bin/env pwsh
# specify 全量产物门禁（skills/specify 专用）
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Specify-HarnessCommon.ps1')

$FeatureDir = ''
$MinBytes = 64
$Extra = [System.Collections.Generic.List[string]]::new()

for ($i = 0; $i -lt $args.Count; $i++) {
    switch ($args[$i]) {
        '--feature-dir' {
            if ($i + 1 -ge $args.Count) { Write-Error 'Error: --feature-dir requires a value'; exit 2 }
            $FeatureDir = $args[++$i]
        }
        '--min-bytes' {
            if ($i + 1 -ge $args.Count) { Write-Error 'Error: --min-bytes requires a value'; exit 2 }
            $MinBytes = $args[++$i]
        }
        { $_ -in '-h', '--help' } {
            Write-Host @'
specify 阶段产物完整性校验（全量门禁）

用法:
  skills/specify/scripts/powershell/verify-specify-artifacts.ps1 --feature-dir <path> [--min-bytes N]

等价于:
  python3 skills/specify/scripts/python/specify_harness.py gate --feature-dir <path> --step all
'@
            exit 0
        }
        default {
            $Extra.Add($args[$i])
        }
    }
}

if (-not $FeatureDir) {
    Write-Error '错误: 必须提供 --feature-dir'
    exit 2
}

$gateArgs = @(
    'gate',
    '--feature-dir', $FeatureDir,
    '--step', 'all',
    '--min-bytes', "$MinBytes"
) + $Extra
Invoke-SpecifyHarness -HarnessArgs $gateArgs

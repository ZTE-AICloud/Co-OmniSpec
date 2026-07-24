#!/usr/bin/env pwsh
# design 全量产物门禁（skills/design 专用）
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Design-HarnessCommon.ps1')

$FeatureDir = ''
$MinBytes = 64
$EnableE2e = $false
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
        '--enable-e2e' {
            $EnableE2e = $true
        }
        { $_ -in '-h', '--help' } {
            Write-Host 'Usage: verify-design-artifacts.ps1 --feature-dir <path> [--min-bytes N] [--enable-e2e]'
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
)
if ($EnableE2e) {
    $gateArgs += '--enable-e2e'
}
$gateArgs += $Extra
Invoke-DesignHarness -HarnessArgs $gateArgs

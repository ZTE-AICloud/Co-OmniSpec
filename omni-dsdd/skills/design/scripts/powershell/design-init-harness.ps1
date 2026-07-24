#!/usr/bin/env pwsh
# 初始化 design harness（skills/design 专用）
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Design-HarnessCommon.ps1')

$PluginRoot = ''
$WorkingDir = ''
$FeatureDir = ''
$Extra = [System.Collections.Generic.List[string]]::new()

for ($i = 0; $i -lt $args.Count; $i++) {
    switch ($args[$i]) {
        '--plugin-root' {
            if ($i + 1 -ge $args.Count) { Write-Error 'Error: --plugin-root requires a value'; exit 2 }
            $PluginRoot = $args[++$i]
        }
        '--working-dir' {
            if ($i + 1 -ge $args.Count) { Write-Error 'Error: --working-dir requires a value'; exit 2 }
            $WorkingDir = $args[++$i]
        }
        '--feature-dir' {
            if ($i + 1 -ge $args.Count) { Write-Error 'Error: --feature-dir requires a value'; exit 2 }
            $FeatureDir = $args[++$i]
        }
        { $_ -in '-h', '--help' } {
            Write-Host 'Usage: ./design-init-harness.ps1 --plugin-root <path> --working-dir <path> --feature-dir <path> [options]'
            exit 0
        }
        default {
            $Extra.Add($args[$i])
        }
    }
}

if (-not $PluginRoot -or -not $WorkingDir -or -not $FeatureDir) {
    Write-Error 'Error: --plugin-root, --working-dir and --feature-dir are required'
    exit 2
}

$initArgs = @(
    'init',
    '--plugin-root', $PluginRoot,
    '--working-dir', $WorkingDir,
    '--feature-dir', $FeatureDir
) + $Extra
Invoke-DesignHarness -HarnessArgs $initArgs

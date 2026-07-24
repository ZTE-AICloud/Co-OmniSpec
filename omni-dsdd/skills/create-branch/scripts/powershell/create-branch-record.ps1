#!/usr/bin/env pwsh
# 持久化分支命名真值 — create-branch harness 封装
$ErrorActionPreference = 'Stop'

$WorkingDir = ''
$PluginRoot = ''
$HarnessArgs = [System.Collections.Generic.List[string]]::new()

for ($i = 0; $i -lt $args.Count; $i++) {
    switch ($args[$i]) {
        '--working-dir' {
            if ($i + 1 -ge $args.Count) { Write-Error 'ERROR: --working-dir requires a value'; exit 1 }
            $WorkingDir = $args[++$i]
        }
        '--plugin-root' {
            if ($i + 1 -ge $args.Count) { Write-Error 'ERROR: --plugin-root requires a value'; exit 1 }
            $PluginRoot = $args[++$i]
        }
        { $_ -in '-h', '--help' } {
            Write-Host 'Usage: ./create-branch-record.ps1 --working-dir <path> --plugin-root <path> record [harness options...]'
            exit 0
        }
        default {
            $HarnessArgs.Add($args[$i])
        }
    }
}

if (-not $WorkingDir -or -not $PluginRoot) {
    Write-Error 'ERROR: --working-dir and --plugin-root are required'
    exit 1
}

$python = Get-Command python3 -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command python -ErrorAction SilentlyContinue }
if (-not $python) {
    Write-Error 'ERROR: python3 or python is required'
    exit 1
}

$HarnessPy = Join-Path $PluginRoot 'skills/create-branch/scripts/python/create_branch_harness.py'
if (-not (Test-Path -LiteralPath $HarnessPy)) {
    Write-Error "ERROR: harness not found: $HarnessPy"
    exit 1
}

$allArgs = @('--working-dir', $WorkingDir) + $HarnessArgs
& $python.Source $HarnessPy @allArgs
exit $LASTEXITCODE

# spec-impact-analyze Harness 公共路径与 Python 调用（PowerShell 封装层）
$ErrorActionPreference = 'Stop'

function Get-ImpactGatePy {
    param(
        [string]$ScriptDir = $PSScriptRoot
    )
    $HarnessPy = Join-Path $ScriptDir '..\python\impact_gate.py'
    $resolved = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($HarnessPy)
    if (-not (Test-Path -LiteralPath $resolved)) {
        Write-Error "ERROR: harness not found: $resolved"
        exit 1
    }
    return $resolved
}

function Get-ImpactPython {
    $python = Get-Command python3 -ErrorAction SilentlyContinue
    if (-not $python) {
        $python = Get-Command python -ErrorAction SilentlyContinue
    }
    if (-not $python) {
        Write-Error 'ERROR: python3 or python is required'
        exit 1
    }
    return $python
}

function Invoke-ImpactGate {
    param(
        [Parameter(Mandatory)]
        [string[]]$GateArgs,
        [string]$ScriptDir = $PSScriptRoot
    )
    $python = Get-ImpactPython
    $GatePy = Get-ImpactGatePy -ScriptDir $ScriptDir
    & $python.Source $GatePy @GateArgs
    exit $LASTEXITCODE
}

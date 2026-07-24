# specify Harness 公共路径与 Python 调用（PowerShell 封装层）
$ErrorActionPreference = 'Stop'

function Get-SpecifyHarnessPy {
    param(
        [string]$ScriptDir = $PSScriptRoot
    )
    $HarnessPy = Join-Path $ScriptDir '..\python\specify_harness.py'
    $resolved = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($HarnessPy)
    if (-not (Test-Path -LiteralPath $resolved)) {
        Write-Error "ERROR: harness not found: $resolved"
        exit 1
    }
    return $resolved
}

function Get-SpecifyPython {
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

function Invoke-SpecifyHarness {
    param(
        [Parameter(Mandatory)]
        [string[]]$HarnessArgs,
        [string]$ScriptDir = $PSScriptRoot
    )
    $python = Get-SpecifyPython
    $HarnessPy = Get-SpecifyHarnessPy -ScriptDir $ScriptDir
    & $python.Source $HarnessPy @HarnessArgs
    exit $LASTEXITCODE
}

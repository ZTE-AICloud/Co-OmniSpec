#!/usr/bin/env pwsh
[CmdletBinding(PositionalBinding = $false)]
param(
    [string]$WorkingDir,
    [string]$HasGit,
    [switch]$Json,
    [string]$BranchName,
    [string]$FeatureDir,
    [switch]$Help,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$RemainingArgs
)
$ErrorActionPreference = 'Stop'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $ScriptDir 'Create-BranchCommon.ps1')

function Show-Help {
    Write-Host "Usage: ./Create-FeatureDir.ps1 -WorkingDir <path> -HasGit <true|false> [-Json] [-BranchName <name>] [-FeatureDir <dir>]"
}

if ($RemainingArgs -and $RemainingArgs.Count -gt 0) {
    $i = 0
    while ($i -lt $RemainingArgs.Count) {
        $arg = $RemainingArgs[$i]
        if ($arg -match '^--(.+)') {
            $paramName = $matches[1]
            switch ($paramName) {
                'json' { $Json = $true }
                'working-dir' {
                    if ($i + 1 -ge $RemainingArgs.Count) { Write-Error "Error: --working-dir requires a value"; exit 1 }
                    $WorkingDir = $RemainingArgs[$i + 1]; $i++
                }
                'has-git' {
                    if ($i + 1 -ge $RemainingArgs.Count) { Write-Error "Error: --has-git requires a value"; exit 1 }
                    $HasGit = $RemainingArgs[$i + 1]; $i++
                }
                'branch-name' {
                    if ($i + 1 -ge $RemainingArgs.Count) { Write-Error "Error: --branch-name requires a value"; exit 1 }
                    $BranchName = $RemainingArgs[$i + 1]; $i++
                }
                'feature-dir' {
                    if ($i + 1 -ge $RemainingArgs.Count) { Write-Error "Error: --feature-dir requires a value"; exit 1 }
                    $FeatureDir = $RemainingArgs[$i + 1]; $i++
                }
                'help' { Show-Help; exit 0 }
                default { Write-Error "Error: Unknown argument: --$paramName"; exit 1 }
            }
        } else {
            Write-Error "Error: Unknown argument: $arg"; exit 1
        }
        $i++
    }
}

if ($Help) { Show-Help; exit 0 }

$workingDir = Test-CreateBranchWorkingDir -WorkingDir $WorkingDir
$hasGit = Test-CreateBranchHasGit -HasGit $HasGit

if ((-not $BranchName -or $BranchName.Trim() -eq '') -and (-not $FeatureDir -or $FeatureDir.Trim() -eq '')) {
    Show-Help
    Write-Error "Error: one of --branch-name or --feature-dir is required."
    exit 1
}

$changesDir = Join-Path $workingDir 'changes'
New-Item -ItemType Directory -Path $changesDir -Force | Out-Null

$branchName = $BranchName
$featureDirResolved = $FeatureDir
$specFile = ''

if ($featureDirResolved -and $featureDirResolved.Trim() -ne '') {
    $featureDirResolved = Resolve-CreateBranchFeatureDirPath -FeatureDirInput $featureDirResolved -WorkingDir $workingDir -ChangesDir $changesDir
} elseif ($branchName -and $branchName.Trim() -ne '') {
    $dirName = ConvertTo-CleanBranchName -Name (Split-Path $branchName -Leaf)
    $featureDirResolved = Join-Path $changesDir $dirName
} else {
    $featureDirResolved = ''
}

if ($featureDirResolved -and $featureDirResolved.Trim() -ne '') {
    New-Item -ItemType Directory -Path $featureDirResolved -Force | Out-Null
    $specFile = Join-Path $featureDirResolved 'spec.md'
}

Write-CreateBranchOutputResults -BranchName $branchName -SpecFile $specFile -FeatureDir $featureDirResolved -HasGit $hasGit -Json:$Json

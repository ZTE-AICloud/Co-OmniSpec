#!/usr/bin/env pwsh
# 组合入口：按需调用 Ensure-GitBranch + Create-FeatureDir（行为与拆分前一致）
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

function Show-Help {
    Write-Host "Usage: ./create-new-feature.ps1 -WorkingDir <path> -HasGit <true|false> [-Json] [-BranchName <name>] [-FeatureDir <dir>]"
    Write-Host ""
    Write-Host "Sub-scripts:"
    Write-Host "  Ensure-GitBranch.ps1   Git branch only"
    Write-Host "  Create-FeatureDir.ps1  Feature directory only"
}

function Parse-WrapperArguments {
    param(
        [string]$WorkingDir,
        [string]$HasGit,
        [switch]$Json,
        [string]$BranchName,
        [string]$FeatureDir,
        [switch]$Help,
        [string[]]$RemainingArgs
    )

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
                    'help' { $Help = $true }
                    default { Write-Error "Error: Unknown argument: --$paramName"; exit 1 }
                }
            } else {
                Write-Error "Error: Unknown argument: $arg"; exit 1
            }
            $i++
        }
    }

    if ($Help) { Show-Help; exit 0 }

    if (-not $WorkingDir -or $WorkingDir.Trim() -eq '') {
        Write-Error "Error: --working-dir is required"; exit 1
    }
    if (-not (Test-Path -LiteralPath $WorkingDir -PathType Container)) {
        Write-Error "Error: --working-dir is not a directory: $WorkingDir"; exit 1
    }
    if (-not $HasGit -or $HasGit.Trim() -eq '') {
        Write-Error "Error: --has-git is required (true or false)"; exit 1
    }
    if ($HasGit -notin @('true', 'false')) {
        Write-Error "Error: --has-git must be true or false"; exit 1
    }

    if ((-not $BranchName -or $BranchName.Trim() -eq '') -and (-not $FeatureDir -or $FeatureDir.Trim() -eq '')) {
        Show-Help
        Write-Error "Error: one of --branch-name or --feature-dir is required."
        exit 1
    }

    return @{
        WorkingDir = $WorkingDir
        HasGit     = $HasGit.Trim().ToLower()
        Json       = [bool]$Json
        BranchName = if ($null -ne $BranchName) { $BranchName } else { '' }
        FeatureDir = if ($null -ne $FeatureDir) { $FeatureDir } else { '' }
    }
}

$parsed = Parse-WrapperArguments -WorkingDir $WorkingDir -HasGit $HasGit -Json:$Json -BranchName $BranchName -FeatureDir $FeatureDir -Help:$Help -RemainingArgs $RemainingArgs

if ($parsed.BranchName -and $parsed.BranchName.Trim() -ne '') {
    $gitArgs = @(
        '-File', (Join-Path $ScriptDir 'Ensure-GitBranch.ps1'),
        '-WorkingDir', $parsed.WorkingDir,
        '-HasGit', $parsed.HasGit,
        '-BranchName', $parsed.BranchName
    )
    & pwsh @gitArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

$dirArgs = @(
    '-File', (Join-Path $ScriptDir 'Create-FeatureDir.ps1'),
    '-WorkingDir', $parsed.WorkingDir,
    '-HasGit', $parsed.HasGit
)
if ($parsed.Json) { $dirArgs += '-Json' }
if ($parsed.BranchName -and $parsed.BranchName.Trim() -ne '') {
    $dirArgs += '-BranchName', $parsed.BranchName
}
if ($parsed.FeatureDir -and $parsed.FeatureDir.Trim() -ne '') {
    $dirArgs += '-FeatureDir', $parsed.FeatureDir
}

& pwsh @dirArgs
exit $LASTEXITCODE

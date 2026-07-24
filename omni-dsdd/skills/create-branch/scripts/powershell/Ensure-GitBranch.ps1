#!/usr/bin/env pwsh
[CmdletBinding(PositionalBinding = $false)]
param(
    [string]$WorkingDir,
    [string]$HasGit,
    [string]$BranchName,
    [switch]$Help,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$RemainingArgs
)
$ErrorActionPreference = 'Stop'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $ScriptDir 'Create-BranchCommon.ps1')

function Show-Help {
    Write-Host "Usage: ./Ensure-GitBranch.ps1 -WorkingDir <path> -HasGit <true|false> -BranchName <name>"
}

if ($RemainingArgs -and $RemainingArgs.Count -gt 0) {
    $i = 0
    while ($i -lt $RemainingArgs.Count) {
        $arg = $RemainingArgs[$i]
        if ($arg -match '^--(.+)') {
            $paramName = $matches[1]
            switch ($paramName) {
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

if (-not $BranchName -or $BranchName.Trim() -eq '') {
    Write-Error "Error: --branch-name is required"
    exit 1
}

function Ensure-GitBranchCore {
    param([string]$Name, [string]$Root, [string]$GitEnabled)

    if ($GitEnabled -ne 'true') {
        Write-Warning "[create-branch] Warning: Git not enabled; skipped branch operation for $Name"
        return
    }

    git -C $Root show-ref --verify --quiet "refs/heads/$Name" 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        git -C $Root checkout $Name 2>$null | Out-Null
        if ($LASTEXITCODE -ne 0) { git -C $Root checkout $Name | Out-Null }
        return
    }

    git -C $Root ls-remote --exit-code --heads origin $Name 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        git -C $Root checkout -b $Name --track "origin/$Name" 2>$null | Out-Null
        if ($LASTEXITCODE -ne 0) { git -C $Root checkout -b $Name --track "origin/$Name" | Out-Null }
        return
    }

    git -C $Root checkout -b $Name 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) { git -C $Root checkout -b $Name | Out-Null }
}

Ensure-GitBranchCore -Name $BranchName -Root $workingDir -GitEnabled $hasGit
$env:SPECIFY_FEATURE = $BranchName

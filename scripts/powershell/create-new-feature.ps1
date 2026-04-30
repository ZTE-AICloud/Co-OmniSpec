#!/usr/bin/env pwsh
[CmdletBinding(PositionalBinding = $false)]
param(
    [switch]$Json,
    [string]$BranchName,
    [string]$FeatureDir,
    [switch]$Help,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$RemainingArgs
)
$ErrorActionPreference = 'Stop'

if ($RemainingArgs -and $RemainingArgs.Count -gt 0) {
    $i = 0
    while ($i -lt $RemainingArgs.Count) {
        $arg = $RemainingArgs[$i]
        if ($arg -match '^--(.+)') {
            $paramName = $matches[1]
            switch ($paramName) {
                'json' { $Json = $true }
                'branch-name' {
                    if ($i + 1 -lt $RemainingArgs.Count) {
                        $BranchName = $RemainingArgs[$i + 1]
                        $i++
                    }
                }
                'feature-dir' {
                    if ($i + 1 -lt $RemainingArgs.Count) {
                        $FeatureDir = $RemainingArgs[$i + 1]
                        $i++
                    }
                }
                'help' { $Help = $true }
            }
        }
        $i++
    }
}

if ($Help) {
    Write-Host "Usage: ./create-new-feature.ps1 [-Json|--json] [-BranchName|--branch-name <name>] [-FeatureDir|--feature-dir <dir>]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -BranchName, --branch-name <name>  Explicit branch name to create or reuse"
    Write-Host "  -FeatureDir, --feature-dir <dir>   Explicit feature directory (absolute path, changes/foo, or foo)"
    Write-Host "  -Json, --json                      Output in JSON format"
    Write-Host "  -Help, --help                      Show this help message"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  ./create-new-feature.ps1 -BranchName 'feature/session-delete-ack'"
    Write-Host "  ./create-new-feature.ps1 -FeatureDir 'changes/session-delete-ack'"
    Write-Host "  ./create-new-feature.ps1 --branch-name 'feature/session-delete-ack' --feature-dir 'session-delete-ack' --json"
    exit 0
}

if ((-not $BranchName -or $BranchName.Trim() -eq '') -and (-not $FeatureDir -or $FeatureDir.Trim() -eq '')) {
    Write-Error "Error: one of -BranchName (--branch-name) or -FeatureDir (--feature-dir) is required."
    exit 1
}

function Find-RepositoryRoot {
    param(
        [string]$StartDir,
        [string[]]$Markers = @('.git', '.infra')
    )

    $current = Resolve-Path $StartDir
    while ($true) {
        foreach ($marker in $Markers) {
            if (Test-Path (Join-Path $current $marker)) {
                return $current
            }
        }

        $parent = Split-Path $current -Parent
        if ($parent -eq $current) {
            return $null
        }
        $current = $parent
    }
}

function ConvertTo-CleanName {
    param([string]$Name)

    return $Name.ToLower() -replace '[^a-z0-9]', '-' -replace '-{2,}', '-' -replace '^-', '' -replace '-$', ''
}

function Resolve-FeatureDirPath {
    param(
        [string]$FeatureDirInput,
        [string]$RepoRoot,
        [string]$ChangesDir
    )

    if (-not $FeatureDirInput -or $FeatureDirInput.Trim() -eq '') {
        return $null
    }

    $trimmed = $FeatureDirInput.Trim().TrimEnd('\', '/')
    if ([System.IO.Path]::IsPathRooted($trimmed)) {
        return $trimmed
    }

    if ($trimmed -match '^(changes[/\\].+)$') {
        return Join-Path $RepoRoot $trimmed
    }

    return Join-Path $ChangesDir $trimmed
}

function Ensure-GitBranch {
    param(
        [string]$TargetBranch,
        [bool]$HasGit
    )

    if (-not $TargetBranch -or $TargetBranch.Trim() -eq '') {
        return
    }

    if (-not $HasGit) {
        Write-Warning "[specify] Warning: Git repository not detected; skipped branch creation for $TargetBranch"
        return
    }

    $localExists = $false
    try {
        git show-ref --verify --quiet "refs/heads/$TargetBranch"
        $localExists = ($LASTEXITCODE -eq 0)
    } catch {
        $localExists = $false
    }

    if ($localExists) {
        git checkout $TargetBranch | Out-Null
        return
    }

    $remoteExists = $false
    try {
        git ls-remote --exit-code --heads origin $TargetBranch 2>$null | Out-Null
        $remoteExists = ($LASTEXITCODE -eq 0)
    } catch {
        $remoteExists = $false
    }

    if ($remoteExists) {
        git checkout -b $TargetBranch --track "origin/$TargetBranch" | Out-Null
    } else {
        git checkout -b $TargetBranch | Out-Null
    }
}

$fallbackRoot = Find-RepositoryRoot -StartDir $PSScriptRoot
if (-not $fallbackRoot) {
    Write-Error "Error: Could not determine repository root. Please run this script from within the repository."
    exit 1
}

try {
    $repoRoot = git rev-parse --show-toplevel 2>$null
    if ($LASTEXITCODE -eq 0) {
        $hasGit = $true
    } else {
        throw "Git not available"
    }
} catch {
    $repoRoot = $fallbackRoot
    $hasGit = $false
}

Set-Location $repoRoot

$changesDir = Join-Path $repoRoot 'changes'
New-Item -ItemType Directory -Path $changesDir -Force | Out-Null

$effectiveBranchName = $BranchName
if ($effectiveBranchName -and $effectiveBranchName.Trim() -ne '') {
    Ensure-GitBranch -TargetBranch $effectiveBranchName -HasGit $hasGit
    $env:SPECIFY_FEATURE = $effectiveBranchName
}

$effectiveFeatureDir = Resolve-FeatureDirPath -FeatureDirInput $FeatureDir -RepoRoot $repoRoot -ChangesDir $changesDir
if ((-not $effectiveFeatureDir -or $effectiveFeatureDir.Trim() -eq '') -and $effectiveBranchName -and $effectiveBranchName.Trim() -ne '') {
    $dirName = ConvertTo-CleanName -Name (Split-Path $effectiveBranchName -Leaf)
    $effectiveFeatureDir = Join-Path $changesDir $dirName
}

$specFile = $null
if ($effectiveFeatureDir -and $effectiveFeatureDir.Trim() -ne '') {
    New-Item -ItemType Directory -Path $effectiveFeatureDir -Force | Out-Null
    $specFile = ""
}

if ($Json) {
    [PSCustomObject]@{
        BRANCH_NAME = $effectiveBranchName
        SPEC_FILE   = $specFile
        FEATURE_DIR = $effectiveFeatureDir
        change_file = $specFile
        FEATURE_NUM = ""
        HAS_GIT     = $hasGit
    } | ConvertTo-Json -Compress
} else {
    Write-Output "BRANCH_NAME: $effectiveBranchName"
    Write-Output "SPEC_FILE: $specFile"
    Write-Output "FEATURE_DIR: $effectiveFeatureDir"
    Write-Output "change_file: $specFile"
    Write-Output "FEATURE_NUM: "
    Write-Output "HAS_GIT: $hasGit"
    if ($effectiveBranchName -and $effectiveBranchName.Trim() -ne '') {
        Write-Output "SPECIFY_FEATURE environment variable set to: $effectiveBranchName"
    }
}


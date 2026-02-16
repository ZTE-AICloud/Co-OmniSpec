#!/usr/bin/env pwsh
# Create a new feature (skill-local script: omni-create-branch)
[CmdletBinding(PositionalBinding = $false)]
param(
    [switch]$Json,
    [string]$ShortName,
    [Parameter(ValueFromPipeline = $false, ValueFromPipelineByPropertyName = $false)]
    [string]$Number = "0",
    [switch]$Help,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$RemainingArgs
)
$ErrorActionPreference = 'Stop'

# Support long-form arguments (--json, --short-name, etc.)
# Parse remaining arguments to handle --format arguments that PowerShell doesn't natively support
if ($RemainingArgs -and $RemainingArgs.Count -gt 0) {
    $i = 0
    while ($i -lt $RemainingArgs.Count) {
        $arg = $RemainingArgs[$i]
        
        if ($arg -match '^--(.+)') {
            $paramName = $matches[1]
            switch ($paramName) {
                'json' { 
                    $Json = $true
                }
                'short-name' { 
                    if ($i + 1 -lt $RemainingArgs.Count) {
                        $ShortName = $RemainingArgs[$i + 1]
                        $i++
                    }
                }
                'number' {
                    if ($i + 1 -lt $RemainingArgs.Count) {
                        $Number = $RemainingArgs[$i + 1]
                        $i++
                    }
                }
                'help' {
                    $Help = $true
                }
            }
        }
        $i++
    }
}

# Show help if requested
if ($Help) {
    Write-Host "Usage: ./create-new-feature.ps1 [-Json|--json] -ShortName|--short-name <name> [-Number|--number N]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -ShortName, --short-name <name>  (Required) Short name for the branch (2-4 words)"
    Write-Host "  -Json, --json                    Output in JSON format"
    Write-Host "  -Number, --number N              Specify branch number manually (overrides auto-detection)"
    Write-Host "  -Help, --help                    Show this help message"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  ./create-new-feature.ps1 -ShortName 'user-auth'"
    Write-Host "  ./create-new-feature.ps1 --json --short-name 'user-auth'"
    Write-Host "  ./create-new-feature.ps1 --short-name 'oauth2-integration' --number 5"
    exit 0
}

# Validate ShortName is provided
if (-not $ShortName -or $ShortName.Trim() -eq "") {
    Write-Error "Error: -ShortName (--short-name) is required."
    Write-Error "Usage: ./create-new-feature.ps1 -ShortName|--short-name <name> [-Json|--json] [-Number|--number N]"
    exit 1
}

# Resolve repository root. Prefer git information when available, but fall back
# to searching for repository markers so the workflow still functions in repositories that
# were initialized with --no-git.
function Find-RepositoryRoot {
    param(
        [string]$StartDir,
        [string[]]$Markers = @('.git', '.specify')
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
            # Reached filesystem root without finding markers
            return $null
        }
        $current = $parent
    }
}

function Get-HighestNumberFromSpecs {
    param([string]$ChangesDir)
    
    $highest = 0
    if (Test-Path $ChangesDir) {
        Get-ChildItem -Path $ChangesDir -Directory | ForEach-Object {
            if ($_.Name -match '^(\d+)') {
                $num = [int]$matches[1]
                if ($num -gt $highest) { $highest = $num }
            }
        }
    }
    return $highest
}

function Get-HighestNumberFromBranches {
    param()
    
    $highest = 0
    try {
        $branches = git branch -a 2>$null
        if ($LASTEXITCODE -eq 0) {
            foreach ($branch in $branches) {
                # Clean branch name: remove leading markers and remote prefixes
                $cleanBranch = $branch.Trim() -replace '^\*?\s+', '' -replace '^remotes/[^/]+/', ''
                
                # Extract feature number if branch matches pattern ###-*
                if ($cleanBranch -match '^(\d+)-') {
                    $num = [int]$matches[1]
                    if ($num -gt $highest) { $highest = $num }
                }
            }
        }
    } catch {
        # If git command fails, return 0
        Write-Verbose "Could not check Git branches: $_"
    }
    return $highest
}

function Get-NextBranchNumber {
    param(
        [string]$ShortName,
        [string]$ChangesDir
    )
    
    # Fetch all remotes to get latest branch info (suppress errors if no remotes)
    try {
        git fetch --all --prune 2>$null | Out-Null
    } catch {
        # Ignore fetch errors
    }
    
    # Find remote branches matching the pattern using git ls-remote
    $remoteBranches = @()
    try {
        $remoteRefs = git ls-remote --heads origin 2>$null
        if ($remoteRefs) {
            $remoteBranches = $remoteRefs | Where-Object { $_ -match "refs/heads/(\d+)-$([regex]::Escape($ShortName))$" } | ForEach-Object {
                if ($_ -match "refs/heads/(\d+)-") {
                    [int]$matches[1]
                }
            }
        }
    } catch {
        # Ignore errors
    }
    
    # Check local branches
    $localBranches = @()
    try {
        $allBranches = git branch 2>$null
        if ($allBranches) {
            $localBranches = $allBranches | Where-Object { $_ -match "^\*?\s*(\d+)-$([regex]::Escape($ShortName))$" } | ForEach-Object {
                if ($_ -match "(\d+)-") {
                    [int]$matches[1]
                }
            }
        }
    } catch {
        # Ignore errors
    }
    
    # Check changes directory
    $specDirs = @()
    if (Test-Path $ChangesDir) {
        try {
            $specDirs = Get-ChildItem -Path $ChangesDir -Directory | Where-Object { $_.Name -match "^(\d+)-$([regex]::Escape($ShortName))$" } | ForEach-Object {
                if ($_.Name -match "^(\d+)-") {
                    # Convert to int to normalize (e.g., "004" -> 4, "4" -> 4)
                    [int]$matches[1]
                }
            }
        } catch {
            # Ignore errors
        }
    }
    
    # Combine all sources and get the highest number
    $maxNum = 0
    foreach ($num in ($remoteBranches + $localBranches + $specDirs)) {
        if ($num -gt $maxNum) {
            $maxNum = $num
        }
    }
    
    # Return next number
    # Ensure we return at least 1 if no branches found
    return [Math]::Max(1, $maxNum + 1)
}

function ConvertTo-CleanBranchName {
    param([string]$Name)
    
    return $Name.ToLower() -replace '[^a-z0-9]', '-' -replace '-{2,}', '-' -replace '^-', '' -replace '-$', ''
}
$fallbackRoot = (Find-RepositoryRoot -StartDir $PSScriptRoot)
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

# Generate branch name from ShortName (required parameter)
# Clean up the short name to ensure it's a valid branch name
$branchSuffix = ConvertTo-CleanBranchName -Name $ShortName

# Determine branch number
# Convert Number to int if it's a string
$numberInt = 0
try {
    $numberInt = [int]$Number
} catch {
    $numberInt = 0
}

if ($numberInt -eq 0) {
    if ($hasGit) {
        # Check existing branches on remotes
        $numberInt = Get-NextBranchNumber -ShortName $branchSuffix -ChangesDir $changesDir
    } else {
        # Fall back to local directory check
        $numberInt = (Get-HighestNumberFromSpecs -ChangesDir $changesDir) + 1
    }
}

# Format feature number with leading zeros (always 3 digits)
# Ensure numberInt is a valid integer
if ($numberInt -lt 0) {
    $numberInt = 0
}
$featureNum = ('{0:000}' -f $numberInt)
$branchName = "$featureNum-$branchSuffix"

# GitHub enforces a 244-byte limit on branch names
# Validate and truncate if necessary
$maxBranchLength = 244
if ($branchName.Length -gt $maxBranchLength) {
    # Calculate how much we need to trim from suffix
    # Account for: feature number (3) + hyphen (1) = 4 chars
    $maxSuffixLength = $maxBranchLength - 4
    
    # Truncate suffix
    $truncatedSuffix = $branchSuffix.Substring(0, [Math]::Min($branchSuffix.Length, $maxSuffixLength))
    # Remove trailing hyphen if truncation created one
    $truncatedSuffix = $truncatedSuffix -replace '-$', ''
    
    $originalBranchName = $branchName
    $branchName = "$featureNum-$truncatedSuffix"
    
    Write-Warning "[specify] Branch name exceeded GitHub's 244-byte limit"
    Write-Warning "[specify] Original: $originalBranchName ($($originalBranchName.Length) bytes)"
    Write-Warning "[specify] Truncated to: $branchName ($($branchName.Length) bytes)"
}

if ($hasGit) {
    try {
        git checkout -b $branchName | Out-Null
    } catch {
        Write-Warning "Failed to create git branch: $branchName"
    }
} else {
    Write-Warning "[specify] Warning: Git repository not detected; skipped branch creation for $branchName"
}

$featureDir = Join-Path $changesDir $branchName
New-Item -ItemType Directory -Path $featureDir -Force | Out-Null

# Template: 始终使用 repo 内 .specify/templates，与现有 specify 命令一致
$template = Join-Path $repoRoot '.specify/templates/spec-template.md'
$specFile = Join-Path $featureDir 'spec.md'
if (Test-Path $template) {
    Copy-Item $template $specFile -Force
} else {
    New-Item -ItemType File -Path $specFile | Out-Null
}

# Set the SPECIFY_FEATURE environment variable for the current session
$env:SPECIFY_FEATURE = $branchName

if ($Json) {
    $obj = [PSCustomObject]@{
        BRANCH_NAME = $branchName
        SPEC_FILE = $specFile
        FEATURE_NUM = $featureNum
        HAS_GIT = $hasGit
    }
    $obj | ConvertTo-Json -Compress
} else {
    Write-Output "BRANCH_NAME: $branchName"
    Write-Output "SPEC_FILE: $specFile"
    Write-Output "FEATURE_NUM: $featureNum"
    Write-Output "HAS_GIT: $hasGit"
    Write-Output "SPECIFY_FEATURE environment variable set to: $branchName"
}

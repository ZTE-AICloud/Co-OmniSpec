#!/usr/bin/env pwsh

# Strict error handling
$ErrorActionPreference = "Stop"

# Parse command line arguments
$IsDesign = $false
$IsImplement = $false

foreach ($arg in $args) {
    switch ($arg) {
        "--design" {
            $IsDesign = $true
        }
        "--implement" {
            $IsImplement = $true
        }
    }
}

# Source common functions
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. "$ScriptDir/common.ps1"

# Get feature paths and validate branch
$paths = Get-FeaturePaths
$repoRoot = $paths.REPO_ROOT
$currentBranch = $paths.CURRENT_BRANCH
$hasGit = $paths.HAS_GIT -eq "true"
$featureDir = $paths.FEATURE_DIR

if (-not (Test-FeatureBranch -Branch $currentBranch -HasGitRepo $hasGit)) {
    exit 1
}

if (-not (Test-Path $featureDir -PathType Container)) {
    Write-Host "ERROR: Feature directory not found: $featureDir" -ForegroundColor Red
    Write-Host "Run /specify first to create the feature structure." -ForegroundColor Red
    exit 1
}

$reviewResultFile = Join-Path $featureDir "review-result.md"
if (Test-Path $reviewResultFile -PathType Leaf) {
    Remove-Item $reviewResultFile -Force
}

# Handle design review times tracking
if ($IsDesign) {
    $designReviewFile = Join-Path $featureDir "design-review-times.md"
    if (Test-Path $designReviewFile -PathType Leaf) {
        # Read current value and increment by 1
        $currentValue = [int](Get-Content $designReviewFile -Raw)
        $newValue = $currentValue + 1
        Set-Content -Path $designReviewFile -Value $newValue -NoNewline
    }
    else {
        # Create file with initial value 1
        Set-Content -Path $designReviewFile -Value "1" -NoNewline
    }
}

# Handle implement review times tracking
if ($IsImplement) {
    $implementReviewFile = Join-Path $featureDir "implement-review-times.md"
    if (Test-Path $implementReviewFile -PathType Leaf) {
        # Read current value and increment by 1
        $currentValue = [int](Get-Content $implementReviewFile -Raw)
        $newValue = $currentValue + 1
        Set-Content -Path $implementReviewFile -Value $newValue -NoNewline
    }
    else {
        # Create file with initial value 1
        Set-Content -Path $implementReviewFile -Value "1" -NoNewline
    }
}

#!/usr/bin/env pwsh

# Consolidated prerequisite checking script
#
# This script provides unified prerequisite checking for Spec-Driven Development workflow.
# It replaces the functionality previously spread across multiple scripts.
#
# Usage: ./mini-check.ps1 [OPTIONS]
#
# OPTIONS:
#   --json              Output in JSON format
#   --help, -h          Show help message
#
# OUTPUTS:
#   JSON mode: {"FEATURE_DIR":"...", "AVAILABLE_DOCS":["..."]}
#   Text mode: FEATURE_DIR:... \n AVAILABLE_DOCS: \n ✓/✗ file.md
#   Paths only: REPO_ROOT: ... \n BRANCH: ... \n FEATURE_DIR: ... etc.

# Parse command line arguments
$JsonMode = $false

foreach ($arg in $args) {
    switch ($arg) {
        "--json" {
            $JsonMode = $true
        }
        { $_ -eq "--help" -or $_ -eq "-h" } {
            @'
Usage: mini-check.ps1 [OPTIONS]

Consolidated prerequisite checking for Spec-Driven Development workflow.

OPTIONS:
  --json              Output in JSON format
  --help, -h          Show this help message

EXAMPLES:
  # Check task prerequisites (design.md required)
  ./mini-check.ps1 --json
'@
            exit 0
        }
        default {
            Write-Host "ERROR: Unknown option '$arg'. Use --help for usage information." -ForegroundColor Red
            exit 1
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
$implPlan = $paths.IMPL_DESIGN

if (-not (Test-FeatureBranch -Branch $currentBranch -HasGitRepo $hasGit)) {
    exit 1
}

if (-not (Test-Path $featureDir -PathType Container)) {
    Write-Host "ERROR: Feature directory not found: $featureDir" -ForegroundColor Red
    Write-Host "Run /specify first to create the feature structure." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $implPlan -PathType Leaf)) {
    Write-Host "ERROR: design.md not found in $featureDir" -ForegroundColor Red
    Write-Host "Run /design first to create the implementation plan." -ForegroundColor Red
    exit 1
}

# Output results
if ($JsonMode) {
    # Minimal JSON paths payload (no validation performed)
    $json = @{
        REPO_ROOT = $repoRoot
        BRANCH = $currentBranch
        FEATURE_DIR = $featureDir
        DESIGN = $implPlan
    } | ConvertTo-Json -Compress
    Write-Host $json
}
else {
    Write-Host "REPO_ROOT: $repoRoot"
    Write-Host "BRANCH: $currentBranch"
    Write-Host "FEATURE_DIR: $featureDir"
    Write-Host "DESIGN: $implPlan"
}

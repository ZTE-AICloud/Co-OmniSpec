#!/usr/bin/env pwsh
# Setup implementation design for a feature

$ErrorActionPreference = 'Stop'

# Parse command line arguments (支持 --json --help 格式，与 Bash 统一)
$Json = $false
$Help = $false

$i = 0
while ($i -lt $args.Count) {
    $arg = $args[$i]
    switch ($arg) {
        '--json' {
            $Json = $true
            $i++
        }
        '--help' {
            $Help = $true
            $i++
        }
        '-h' {
            $Help = $true
            $i++
        }
        default {
            Write-Error "Unknown option '$arg'. Use --help for usage information."
            exit 1
        }
    }
}

# Show help if requested
if ($Help) {
    Write-Output "Usage: ./setup-design.ps1 [--json] [--help]"
    Write-Output "  --json     Output results in JSON format"
    Write-Output "  --help, -h Show this help message"
    exit 0
}

# Load common functions
. "$PSScriptRoot/common.ps1"

# Get all paths and variables from common functions
$paths = Get-FeaturePathsEnv

# Check if we're on a proper feature branch (only for git repos)
if (-not (Test-FeatureBranch -Branch $paths.CURRENT_BRANCH -HasGit $paths.HAS_GIT)) { 
    exit 1 
}

# Ensure the feature directory exists
New-Item -ItemType Directory -Path $paths.FEATURE_DIR -Force | Out-Null

# Copy design template if it exists (.omni-infra or omni-infra)
$template = $null
foreach ($infraDir in @('.omni-infra', 'omni-infra')) {
    $candidate = Join-Path $paths.REPO_ROOT "$infraDir/templates/design-template.md"
    if (Test-Path $candidate) {
        $template = $candidate
        break
    }
}
if ($template) {
    Copy-Item $template $paths.IMPL_DESIGN -Force
    $date = Get-Date -Format 'yyyy-MM-dd'
    (Get-Content $paths.IMPL_DESIGN -Raw) `
        -replace '\[FEATURE\]', $paths.CURRENT_BRANCH `
        -replace '\[###-feature-name\]', $paths.CURRENT_BRANCH `
        -replace '\[DATE\]', $date `
        -replace '\[link\]', 'spec.md' |
        Set-Content $paths.IMPL_DESIGN -Encoding UTF8
    Write-Output "Copied design template to $($paths.IMPL_DESIGN)"
} else {
    Write-Warning 'Design template not found under .omni-infra/ or omni-infra/templates/'
    New-Item -ItemType File -Path $paths.IMPL_DESIGN -Force | Out-Null
}

# Output results
if ($Json) {
    $result = [PSCustomObject]@{ 
        FEATURE_SPEC = $paths.FEATURE_SPEC
        IMPL_DESIGN = $paths.IMPL_DESIGN
        CHANGES_DIR = $paths.FEATURE_DIR
        BRANCH = $paths.CURRENT_BRANCH
        HAS_GIT = $paths.HAS_GIT
    }
    $result | ConvertTo-Json -Compress
} else {
    Write-Output "FEATURE_SPEC: $($paths.FEATURE_SPEC)"
    Write-Output "IMPL_DESIGN: $($paths.IMPL_DESIGN)"
    Write-Output "CHANGES_DIR: $($paths.FEATURE_DIR)"
    Write-Output "BRANCH: $($paths.CURRENT_BRANCH)"
    Write-Output "HAS_GIT: $($paths.HAS_GIT)"
}

#!/usr/bin/env pwsh
# Initialize tasks harness for a feature

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
    Write-Output "Usage: ./tasks-init-harness.ps1 [--json] [--help]"
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

# Ensure subdirectories exist
$subDirs = @('contracts', '.runs/evaluations', '.runs/metrics', '.runs/internal', 'checklists')
foreach ($subDir in $subDirs) {
    New-Item -ItemType Directory -Path (Join-Path $paths.FEATURE_DIR $subDir) -Force | Out-Null
}

# Copy tasks template if it exists (.omni-infra or omni-infra)
$template = $null
foreach ($infraDir in @('.omni-infra', 'omni-infra')) {
    $candidate = Join-Path $paths.REPO_ROOT "$infraDir/templates/tasks-template.md"
    if (Test-Path $candidate) {
        $template = $candidate
        break
    }
}

$tasksFile = Join-Path $paths.FEATURE_DIR 'tasks.md'
if ($template) {
    Copy-Item $template $tasksFile -Force
    $date = Get-Date -Format 'yyyy-MM-dd'
    (Get-Content $tasksFile -Raw) `
        -replace '\[FEATURE\]', $paths.CURRENT_BRANCH `
        -replace '\[###-feature-name\]', $paths.CURRENT_BRANCH `
        -replace '\[DATE\]', $date `
        -replace '\[link\]', 'spec.md' |
        Set-Content $tasksFile -Encoding UTF8
    Write-Output "Copied tasks template to $tasksFile"
} else {
    Write-Warning 'Tasks template not found under .omni-infra/ or omni-infra/templates/'
    New-Item -ItemType File -Path $tasksFile -Force | Out-Null
}

# Create initial state file for tasks phase
$stateFile = Join-Path $paths.FEATURE_DIR '.runs/tasks-run.json'
$createdAt = (Get-Date).ToUniversalTime().ToString('o')
$stateContent = @"
{
  "phase": "tasks",
  "status": "initialized",
  "branch": "$($paths.CURRENT_BRANCH)",
  "feature_dir": "$($paths.FEATURE_DIR)",
  "tasks_file": "$tasksFile",
  "spec_file": "$($paths.FEATURE_SPEC)",
  "design_file": "$($paths.IMPL_DESIGN)",
  "completed_stages": [],
  "current_stage": null,
  "created_at": "$createdAt"
}
"@
Set-Content -Path $stateFile -Value $stateContent -Encoding UTF8

# Output results
if ($Json) {
    $result = [PSCustomObject]@{
        TASKS_FILE = $tasksFile
        STATE_FILE = $stateFile
        CHANGES_DIR = $paths.FEATURE_DIR
        BRANCH = $paths.CURRENT_BRANCH
        HAS_GIT = $paths.HAS_GIT
    }
    $result | ConvertTo-Json -Compress
} else {
    Write-Output "TASKS_FILE: $tasksFile"
    Write-Output "STATE_FILE: $stateFile"
    Write-Output "CHANGES_DIR: $($paths.FEATURE_DIR)"
    Write-Output "BRANCH: $($paths.CURRENT_BRANCH)"
    Write-Output "HAS_GIT: $($paths.HAS_GIT)"
}
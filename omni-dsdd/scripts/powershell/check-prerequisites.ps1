#!/usr/bin/env pwsh

# Consolidated prerequisite checking script (PowerShell)
#
# This script provides unified prerequisite checking for Spec-Driven Development workflow.
# It replaces the functionality previously spread across multiple scripts.
#
# Usage: ./check-prerequisites.ps1 [OPTIONS]
#
# OPTIONS:
#   --json              Output in JSON format
#   --require-tasks     Require tasks.md to exist (for implementation phase)
#   --include-tasks     Include tasks.md in AVAILABLE_DOCS list
#   --paths-only        Only output path variables (no validation)
#   --help, -h          Show help message

$ErrorActionPreference = 'Stop'

# Parse command line arguments (支持 --json --require-tasks 格式，与 Bash 统一)
$Json = $false
$RequireTasks = $false
$IncludeTasks = $false
$PathsOnly = $false
$Help = $false
$WorkingDirArg = ""
$PluginRootArg = ""

$i = 0
while ($i -lt $args.Count) {
    $arg = $args[$i]
    switch ($arg) {
        '--json' {
            $Json = $true
            $i++
        }
        '--require-tasks' {
            $RequireTasks = $true
            $i++
        }
        '--include-tasks' {
            $IncludeTasks = $true
            $i++
        }
        '--paths-only' {
            $PathsOnly = $true
            $i++
        }
        '--working-dir' {
            if ($i + 1 -ge $args.Count) { Write-Error 'ERROR: --working-dir requires a value'; exit 1 }
            $WorkingDirArg = $args[$i + 1]
            $i += 2
        }
        '--plugin-root' {
            if ($i + 1 -ge $args.Count) { Write-Error 'ERROR: --plugin-root requires a value'; exit 1 }
            $PluginRootArg = $args[$i + 1]
            $i += 2
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
    Write-Output @"
Usage: check-prerequisites.ps1 [OPTIONS]

Consolidated prerequisite checking for Spec-Driven Development workflow.

OPTIONS:
  --json              Output in JSON format
  --require-tasks     Require tasks.md to exist (for implementation phase)
  --include-tasks     Include tasks.md in AVAILABLE_DOCS list
  --paths-only        Only output path variables (no prerequisite validation)
  --help, -h          Show this help message

EXAMPLES:
  # Check task prerequisites (design.md required)
  .\check-prerequisites.ps1 --json
  
  # Check implementation prerequisites (design.md + tasks.md required)
  .\check-prerequisites.ps1 --json --require-tasks --include-tasks
  
  # Get feature paths only (no validation)
  .\check-prerequisites.ps1 --paths-only

"@
    exit 0
}

# Source common functions
. "$PSScriptRoot/common.ps1"

if ($WorkingDirArg) {
    $env:CLAUDE_WORKING_DIR = (Resolve-Path -LiteralPath $WorkingDirArg).Path
}
if ($PluginRootArg) {
    $env:CLAUDE_PLUGIN_ROOT = (Resolve-Path -LiteralPath $PluginRootArg).Path
}

# Get feature paths
$paths = Get-FeaturePathsEnv

# If paths-only mode, output paths and exit (support combined -Json -PathsOnly)
# Note: In paths-only mode, we skip branch validation to allow reverse command
# to work on any branch (including main/master)
if ($PathsOnly) {
    if ($Json) {
        [PSCustomObject]@{
            PLUGIN_ROOT  = $paths.PLUGIN_ROOT
            WORKING_DIR  = $paths.WORKING_DIR
            REPO_ROOT    = $paths.REPO_ROOT
            BRANCH       = $paths.CURRENT_BRANCH
            FEATURE_DIR  = $paths.FEATURE_DIR
            FEATURE_SPEC = $paths.FEATURE_SPEC
            IMPL_DESIGN    = $paths.IMPL_DESIGN
            TASKS        = $paths.TASKS
            DOC_DIR      = $paths.DOC_DIR
            DOC_SPECS_DIR = $paths.DOC_SPECS_DIR
            DOC_RULES_DIR = $paths.DOC_RULES_DIR
            DOC_NAVIGATIONS_DIR = $paths.DOC_NAVIGATIONS_DIR
        } | ConvertTo-Json -Compress
    } else {
        Write-Output "PLUGIN_ROOT: $($paths.PLUGIN_ROOT)"
        Write-Output "WORKING_DIR: $($paths.WORKING_DIR)"
        Write-Output "REPO_ROOT: $($paths.REPO_ROOT)"
        Write-Output "BRANCH: $($paths.CURRENT_BRANCH)"
        Write-Output "FEATURE_DIR: $($paths.FEATURE_DIR)"
        Write-Output "FEATURE_SPEC: $($paths.FEATURE_SPEC)"
        Write-Output "IMPL_DESIGN: $($paths.IMPL_DESIGN)"
        Write-Output "TASKS: $($paths.TASKS)"
        Write-Output "DOC_DIR: $($paths.DOC_DIR)"
        Write-Output "DOC_SPECS_DIR: $($paths.DOC_SPECS_DIR)"
        Write-Output "DOC_RULES_DIR: $($paths.DOC_RULES_DIR)"
        Write-Output "DOC_NAVIGATIONS_DIR: $($paths.DOC_NAVIGATIONS_DIR)"
    }
    exit 0
}

# Validate branch (only when not in paths-only mode)
if (-not (Test-FeatureBranch -Branch $paths.CURRENT_BRANCH -HasGit:$paths.HAS_GIT)) { 
    exit 1 
}

# Validate required directories and files
if (-not (Test-Path $paths.FEATURE_DIR -PathType Container)) {
    Write-Output "ERROR: Feature directory not found: $($paths.FEATURE_DIR)"
    Write-Output "Run /specify first to create the feature structure."
    exit 1
}

if (-not (Test-Path $paths.IMPL_DESIGN -PathType Leaf)) {
    Write-Output "ERROR: design.md not found in $($paths.FEATURE_DIR)"
    Write-Output "Run /design first to create the implementation design."
    exit 1
}

# Check for tasks.md if required
if ($RequireTasks -and -not (Test-Path $paths.TASKS -PathType Leaf)) {
    Write-Output "ERROR: tasks.md not found in $($paths.FEATURE_DIR)"
    Write-Output "Run /tasks first to create the task list."
    exit 1
}

# Build list of available documents
$docs = @()

# Always check these optional docs
if (Test-Path $paths.RESEARCH) { $docs += 'research.md' }
if (Test-Path $paths.DATA_MODEL) { $docs += 'data-model.md' }

# Check contracts directory (only if it exists and has files)
if ((Test-Path $paths.CONTRACTS_DIR) -and (Get-ChildItem -Path $paths.CONTRACTS_DIR -ErrorAction SilentlyContinue | Select-Object -First 1)) { 
    $docs += 'contracts/' 
}

if (Test-Path $paths.QUICKSTART) { $docs += 'quickstart.md' }

# Include tasks.md if requested and it exists
if ($IncludeTasks -and (Test-Path $paths.TASKS)) { 
    $docs += 'tasks.md' 
}

# Output results
if ($Json) {
    # JSON output
    [PSCustomObject]@{ 
        FEATURE_DIR = $paths.FEATURE_DIR
        WORKING_DIR = $paths.WORKING_DIR
        AVAILABLE_DOCS = $docs
        DOC_DIR = $paths.DOC_DIR
        DOC_SPECS_DIR = $paths.DOC_SPECS_DIR
        DOC_RULES_DIR = $paths.DOC_RULES_DIR
        DOC_NAVIGATIONS_DIR = $paths.DOC_NAVIGATIONS_DIR
    } | ConvertTo-Json -Compress
} else {
    # Text output
    Write-Output "FEATURE_DIR:$($paths.FEATURE_DIR)"
    Write-Output "WORKING_DIR:$($paths.WORKING_DIR)"
    Write-Output "AVAILABLE_DOCS:"
    
    # Show status of each potential document
    Test-FileExists -Path $paths.RESEARCH -Description 'research.md' | Out-Null
    Test-FileExists -Path $paths.DATA_MODEL -Description 'data-model.md' | Out-Null
    Test-DirHasFiles -Path $paths.CONTRACTS_DIR -Description 'contracts/' | Out-Null
    Test-FileExists -Path $paths.QUICKSTART -Description 'quickstart.md' | Out-Null
    
    if ($IncludeTasks) {
        Test-FileExists -Path $paths.TASKS -Description 'tasks.md' | Out-Null
    }
}

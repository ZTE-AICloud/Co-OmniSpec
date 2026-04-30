#!/usr/bin/env pwsh

# Strict error handling
$ErrorActionPreference = "Stop"

# Parse command line arguments
$JsonMode = $false
$ShortName = ""
$FeatureDescription = ""
$argsArray = [System.Collections.ArrayList]@()

$i = 0
while ($i -lt $args.Count) {
    $arg = $args[$i]

    switch ($arg) {
        "--json" {
            $JsonMode = $true
        }
        "--short-name" {
            if ($i + 1 -ge $args.Count) {
                Write-Host "Error: --short-name requires a value" -ForegroundColor Red
                exit 1
            }
            $nextArg = $args[$i + 1]
            # Check if the next argument is another option (starts with --)
            if ($nextArg -match "^--") {
                Write-Host "Error: --short-name requires a value" -ForegroundColor Red
                exit 1
            }
            $ShortName = $nextArg
            $i++  # Skip next argument
        }
        { $_ -eq "--help" -or $_ -eq "-h" } {
            @'
Usage: ./mini-create-new-feature.ps1 [--json] [--short-name <name>] <feature_description>

Options:
  --json              Output in JSON format
  --short-name <name> Provide a custom short name (2-4 words) for the branch
  --help, -h          Show this help message

Examples:
  ./mini-create-new-feature.ps1 'Add user authentication system' --short-name 'user-auth'
  ./mini-create-new-feature.ps1 'Implement OAuth2 integration for API'
'@
            exit 0
        }
        default {
            [void]$argsArray.Add($arg)
        }
    }
    $i++
}

$FeatureDescription = $argsArray -join " "
if ([string]::IsNullOrWhiteSpace($FeatureDescription)) {
    Write-Host "Usage: ./mini-create-new-feature.ps1 [--json] [--short-name <name>] <feature_description>" -ForegroundColor Red
    exit 1
}

# Function to find the repository root by searching for existing project markers
function Find-RepoRoot {
    param([string]$StartDir)

    $currentDir = $StartDir
    while ($currentDir -ne "/") {
        if (Test-Path (Join-Path $currentDir ".git") -PathType Container) {
            return $currentDir
        }
        if (Test-Path (Join-Path $currentDir ".infra") -PathType Container) {
            return $currentDir
        }
        $currentDir = Split-Path $currentDir -Parent
        if ([string]::IsNullOrEmpty($currentDir)) {
            break
        }
    }
    return $null
}

# Function to generate branch name with stop word filtering and length filtering
function Generate-BranchName {
    param([string]$Description)

    # Common stop words to filter out
    $stopWords = @(
        'i', 'a', 'an', 'the', 'to', 'for', 'of', 'in', 'on', 'at', 'by', 'with', 'from',
        'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
        'do', 'does', 'did', 'will', 'would', 'should', 'could', 'can', 'may', 'might', 'must', 'shall',
        'this', 'that', 'these', 'those', 'my', 'your', 'our', 'their',
        'want', 'need', 'add', 'get', 'set'
    )

    # Convert to lowercase and split into words
    $cleanName = $Description -replace '[^a-zA-Z0-9]', ' ' -replace '\s+', ' '.Trim().ToLower()
    $words = $cleanName -split ' '

    # Filter words: remove stop words and words shorter than 3 chars
    $meaningfulWords = @()
    foreach ($word in $words) {
        if ([string]::IsNullOrWhiteSpace($word)) {
            continue
        }

        # Keep words that are NOT stop words AND (length >= 3 OR are potential acronyms)
        if ($stopWords -notcontains $word) {
            if ($word.Length -ge 3) {
                $meaningfulWords += $word
            }
            else {
                # Keep short words if they appear as uppercase in original (likely acronyms)
                $upperWord = $word.ToUpper()
                if ($Description -match "\b$upperWord\b") {
                    $meaningfulWords += $word
                }
            }
        }
    }

    # If we have meaningful words, use first 3-4 of them
    if ($meaningfulWords.Count -gt 0) {
        $maxWords = 3
        if ($meaningfulWords.Count -eq 4) {
            $maxWords = 4
        }

        $result = ""
        for ($j = 0; $j -lt [Math]::Min($maxWords, $meaningfulWords.Count); $j++) {
            if ($result -ne "") {
                $result += "-"
            }
            $result += $meaningfulWords[$j]
        }
        return $result
    }
    else {
        # Fallback to original logic if no meaningful words found
        $fallbackWords = $cleanName -split ' ' | Where-Object { $_ -ne "" } | Select-Object -First 3
        return ($fallbackWords -join "-")
    }
}

# Resolve repository root
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$null = git rev-parse --show-toplevel 2>$null
if ($LASTEXITCODE -eq 0) {
    $RepoRoot = git rev-parse --show-toplevel
    $HasGit = $true
}
else {
    $RepoRoot = Find-RepoRoot -StartDir $ScriptDir
    if ([string]::IsNullOrEmpty($RepoRoot)) {
        Write-Host "Error: Could not determine repository root. Please run this script from within the repository." -ForegroundColor Red
        exit 1
    }
    $HasGit = $false
}

Set-Location $RepoRoot

$ChangesDir = Join-Path $RepoRoot "changes"
$null = New-Item -ItemType Directory -Force -Path $ChangesDir

# Find highest feature number
$Highest = 0
if (Test-Path $ChangesDir -PathType Container) {
    Get-ChildItem $ChangesDir -Directory | ForEach-Object {
        $dirname = $_.Name
        if ($dirname -match "^(\d+)") {
            $number = [int]$matches[1]
            if ($number -gt $Highest) {
                $Highest = $number
            }
        }
    }
}

$Next = $Highest + 1
$FeatureNum = "{0:D3}" -f $Next

# Generate branch name
if (-not [string]::IsNullOrWhiteSpace($ShortName)) {
    # Use provided short name, just clean it up
    $BranchSuffix = $ShortName.ToLower() -replace '[^a-z0-9]', '-' -replace '-+', '-' -replace '^-' -replace '-$'
}
else {
    # Generate from description with smart filtering
    $BranchSuffix = Generate-BranchName -Description $FeatureDescription
}

$BranchName = "${FeatureNum}-${BranchSuffix}"

# GitHub enforces a 244-byte limit on branch names
# Validate and truncate if necessary
$MaxBranchLength = 244
$BranchNameBytes = [System.Text.Encoding]::UTF8.GetByteCount($BranchName)

if ($BranchNameBytes -gt $MaxBranchLength) {
    # Calculate how much we need to trim from suffix
    # Account for: feature number (3) + hyphen (1) = 4 chars
    $MaxSuffixLength = $MaxBranchLength - 4

    # Truncate suffix (use character count, but ensure we don't cut mid-byte for multi-byte)
    $TruncatedSuffix = $BranchSuffix.Substring(0, [Math]::Min($MaxSuffixLength, $BranchSuffix.Length))
    # Remove trailing hyphen if truncation created one
    $TruncatedSuffix = $TruncatedSuffix -trim('-')

    $OriginalBranchName = $BranchName
    $BranchName = "${FeatureNum}-${TruncatedSuffix}"

    Write-Host "[specify] Warning: Branch name exceeded GitHub's 244-byte limit" -ForegroundColor Yellow
    Write-Host "[specify] Original: $OriginalBranchName ($BranchNameBytes bytes)" -ForegroundColor Yellow
    Write-Host "[specify] Truncated to: $BranchName ($([System.Text.Encoding]::UTF8.GetByteCount($BranchName)) bytes)" -ForegroundColor Yellow
}

if ($HasGit) {
    git checkout -b $BranchName
}
else {
    Write-Host "[specify] Warning: Git repository not detected; skipped branch creation for $BranchName" -ForegroundColor Yellow
}

$FeatureDir = Join-Path $ChangesDir $BranchName
$null = New-Item -ItemType Directory -Force -Path $FeatureDir

$Template = Join-Path $RepoRoot ".infra" "templates" "mini-design-template.md"
$SpecFile = Join-Path $FeatureDir "design.md"

if (Test-Path $Template -PathType Leaf) {
    Copy-Item $Template $SpecFile
}
else {
    $null = New-Item -ItemType File -Force -Path $SpecFile
}

# Set the SPECIFY_FEATURE environment variable for the current session
$env:SPECIFY_FEATURE = $BranchName

if ($JsonMode) {
    $result = @{
        BRANCH_NAME = $BranchName
        SPEC_FILE = $SpecFile
        FEATURE_NUM = $FeatureNum
        FEATURE_DIR = $FeatureDir
    } | ConvertTo-Json -Compress
    Write-Host $result
}
else {
    Write-Host "BRANCH_NAME: $BranchName"
    Write-Host "SPEC_FILE: $SpecFile"
    Write-Host "FEATURE_NUM: $FeatureNum"
    Write-Host "FEATURE_DIR: $FeatureDir"
    Write-Host "SPECIFY_FEATURE environment variable set to: $BranchName"
}

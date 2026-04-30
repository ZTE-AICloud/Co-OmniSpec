#!/usr/bin/env pwsh

# Common PowerShell helper functions for OmniSpec.

$ErrorActionPreference = 'Stop'

function Get-RepoRoot {
    try {
        $result = git rev-parse --show-toplevel 2>$null
        if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrEmpty($result)) {
            return $result
        }
    } catch {
        # ignore and fall back
    }

    # Fallback: resolve from script location
    return (Resolve-Path (Join-Path $PSScriptRoot "../../..")).Path
}

function Get-CurrentBranch {
    if ($env:SPECIFY_FEATURE) {
        return $env:SPECIFY_FEATURE
    }

    try {
        $result = git rev-parse --abbrev-ref HEAD 2>$null
        if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrEmpty($result)) {
            return $result
        }
    } catch {
        # ignore and fall back
    }

    $repoRoot = Get-RepoRoot
    $changesDir = Join-Path $repoRoot "changes"

    if (Test-Path -Path $changesDir -PathType Container) {
        $latestFeature = ""
        $highest = -1
        Get-ChildItem -Path $changesDir -Directory | ForEach-Object {
            if ($_.Name -match '^(\d{3})-') {
                $num = [int]$matches[1]
                if ($num -gt $highest) {
                    $highest = $num
                    $latestFeature = $_.Name
                }
            }
        }
        if ($latestFeature) {
            return $latestFeature
        }
    }

    return "main"
}

function Test-HasGit {
    try {
        git rev-parse --show-toplevel 2>$null | Out-Null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

function Test-FeatureBranch {
    param(
        [string]$Branch,
        [bool]$HasGit = $true
    )

    if (-not $HasGit) {
        Write-Warning "[omnispec] Git repository not detected; skipped branch validation"
        return $true
    }

    if ($Branch -notmatch '^[0-9]{3}-') {
        Write-Output "ERROR: Not on a feature branch. Current branch: $Branch"
        Write-Output "Feature branches should be named like: 001-feature-name"
        return $false
    }

    return $true
}

function Get-FeatureDir {
    param(
        [string]$RepoRoot,
        [string]$Branch
    )
    Join-Path $RepoRoot "changes/$Branch"
}

function Get-FeaturePathsEnv {
    $repoRoot = Get-RepoRoot
    $currentBranch = Get-CurrentBranch
    $hasGit = Test-HasGit
    $featureDir = Get-FeatureDir -RepoRoot $repoRoot -Branch $currentBranch

    $docDir = Join-Path $repoRoot "omni-doc"
    [PSCustomObject]@{
        REPO_ROOT = $repoRoot
        CURRENT_BRANCH = $currentBranch
        HAS_GIT = $hasGit
        FEATURE_DIR = $featureDir

        FEATURE_SPEC = Join-Path $featureDir "spec.md"
        IMPL_DESIGN = Join-Path $featureDir "design.md"
        TASKS = Join-Path $featureDir "tasks.md"
        RESEARCH = Join-Path $featureDir "research.md"
        DATA_MODEL = Join-Path $featureDir "data-model.md"
        QUICKSTART = Join-Path $featureDir "quickstart.md"
        CONTRACTS_DIR = Join-Path $featureDir "contracts"

        DOC_DIR = $docDir
        DOC_SPECS_DIR = Join-Path $docDir "specs"
        DOC_RULES_DIR = Join-Path $docDir "rules"
        DOC_NAVIGATIONS_DIR = Join-Path $docDir "navigations"
    }
}

function Test-FileExists {
    param(
        [string]$Path,
        [string]$Description
    )
    if (Test-Path -Path $Path -PathType Leaf) {
        Write-Output "  [OK] $Description"
        return $true
    }

    Write-Output "  [FAIL] $Description"
    return $false
}

function Test-DirHasFiles {
    param(
        [string]$Path,
        [string]$Description
    )

    if (-not (Test-Path -Path $Path -PathType Container)) {
        Write-Output "  [FAIL] $Description"
        return $false
    }

    $firstFile = Get-ChildItem -Path $Path -ErrorAction SilentlyContinue |
        Where-Object { -not $_.PSIsContainer } |
        Select-Object -First 1

    if ($null -ne $firstFile) {
        Write-Output "  [OK] $Description"
        return $true
    }

    Write-Output "  [FAIL] $Description"
    return $false
}

function Normalize-Path {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Path,
        [string]$BasePath = ""
    )

    if ([string]::IsNullOrWhiteSpace($Path)) {
        return $null
    }

    if ([string]::IsNullOrWhiteSpace($BasePath)) {
        $BasePath = Get-RepoRoot
    }

    if ($Path.StartsWith("~")) {
        $Path = $Path -replace "^~", $env:HOME
    }

    if ([System.IO.Path]::IsPathRooted($Path)) {
        try {
            return (Resolve-Path -LiteralPath $Path -ErrorAction Stop).Path
        } catch {
            return [System.IO.Path]::GetFullPath($Path)
        }
    }

    $fullPath = Join-Path -Path $BasePath -ChildPath $Path
    try {
        if (Test-Path -LiteralPath $fullPath -ErrorAction SilentlyContinue) {
            return (Resolve-Path -LiteralPath $fullPath -ErrorAction Stop).Path
        }
    } catch {
        # ignore and fall back
    }

    return [System.IO.Path]::GetFullPath($fullPath)
}

function Get-OutputDir {
    param(
        [string]$UserOutputDir = "",
        [Parameter(Mandatory=$true)]
        [string]$ElementOutputDir,
        [string]$CurrentBranch = "",
        [string]$FeatureDir = "",
        [Parameter(Mandatory=$true)]
        [string]$RepoRoot
    )

    if (-not [string]::IsNullOrEmpty($UserOutputDir)) {
        $outputDir = Normalize-Path -Path $UserOutputDir -BasePath $RepoRoot
        if (-not (Test-Path -Path $outputDir -PathType Container)) {
            New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
        }
        return $outputDir
    }

    $isFeatureBranch = $false
    if (-not [string]::IsNullOrEmpty($CurrentBranch)) {
        $isFeatureBranch = ($CurrentBranch -match '^\d{3}-')
    }

    if ($isFeatureBranch -and -not [string]::IsNullOrEmpty($FeatureDir)) {
        $outputDir = Join-Path -Path $FeatureDir -ChildPath $ElementOutputDir
    } else {
        $outputDir = Join-Path -Path $RepoRoot -ChildPath ("omni-doc/$ElementOutputDir")
    }

    $outputDir = Normalize-Path -Path $outputDir -BasePath $RepoRoot
    if (-not (Test-Path -Path $outputDir -PathType Container)) {
        New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
    }

    return $outputDir
}

function Wait-ForBatchesCompletion {
    param(
        [Parameter(Mandatory=$true)]
        [string]$RepoRoot,
        [Parameter(Mandatory=$true)]
        [string]$BatchNumbersJson,
        [Parameter(Mandatory=$true)]
        [string]$StageType,
        [int]$MaxWaitMinutes = 30,
        [int]$CheckIntervalSeconds = 30
    )

    if ([string]::IsNullOrEmpty($RepoRoot) -or
        [string]::IsNullOrEmpty($BatchNumbersJson) -or
        [string]::IsNullOrEmpty($StageType)) {
        Write-Error "Wait-ForBatchesCompletion: missing required parameters"
        return 1
    }

    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $verifyScript = Join-Path $scriptDir "verify-batches-completion.ps1"
    if (-not (Test-Path -Path $verifyScript -PathType Leaf)) {
        Write-Error "Wait-ForBatchesCompletion: verify script not found: $verifyScript"
        return 1
    }

    $maxWaitSeconds = $MaxWaitMinutes * 60
    $elapsedSeconds = 0
    $iteration = 0

    while ($elapsedSeconds -lt $maxWaitSeconds) {
        $iteration++
        try {
            $verifyResult = & $verifyScript -RepoRoot $RepoRoot -BatchNumbers $BatchNumbersJson -StageType $StageType 2>&1
            $verifyOutput = $verifyResult | Out-String
            $verifyJson = $verifyOutput | ConvertFrom-Json

            if ($verifyJson.all_completed) {
                $completedCount = $verifyJson.completed_count
                $totalCount = $verifyJson.total_count
                Write-Host "All batches completed ($completedCount/$totalCount)"
                return 0
            }
        } catch {
            # ignore and wait
        }

        Start-Sleep -Seconds $CheckIntervalSeconds
        $elapsedSeconds += $CheckIntervalSeconds
    }

    Write-Error "Wait-ForBatchesCompletion: timeout after $MaxWaitMinutes minutes"
    return 1
}

function Get-ProjectName {
    param(
        [Parameter(Mandatory=$true)]
        [string]$RepoRoot
    )

    if ($env:OMNISPEC_PROJECT_NAME) {
        return $env:OMNISPEC_PROJECT_NAME
    }

    $configFile = Join-Path $RepoRoot ".infra/config.yaml"
    if (Test-Path -Path $configFile -PathType Leaf) {
        try {
            if (Get-Command yq -ErrorAction SilentlyContinue) {
                $projectName = yq -r '.project_name // empty' $configFile 2>$null
                if (-not [string]::IsNullOrEmpty($projectName)) {
                    return $projectName
                }
            } elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
                $projectName = python3 -c 'import yaml, sys; data=yaml.safe_load(open(sys.argv[1])); print((data or {}).get("project_name",""))' $configFile 2>$null
                if (-not [string]::IsNullOrEmpty($projectName)) {
                    return $projectName
                }
            } else {
                foreach ($line in (Get-Content $configFile -ErrorAction SilentlyContinue)) {
                    if ($line -match '^\s*project_name\s*:') {
                        $value = ($line -replace '^\s*project_name\s*:\s*', '').Trim()
                        if ($value.Length -ge 2) {
                            $startsWithSingle = $value.StartsWith("'")
                            $startsWithDouble = $value.StartsWith('"')
                            if (($startsWithSingle -and $value.EndsWith("'")) -or ($startsWithDouble -and $value.EndsWith('"'))) {
                                $value = $value.Substring(1, $value.Length - 2)
                            }
                        }
                        if (-not [string]::IsNullOrEmpty($value)) {
                            return $value
                        }
                    }
                }
            }
        } catch {
            # ignore
        }
    }

    $projectNameFile = Join-Path $RepoRoot ".infra/project-name"
    if (Test-Path -Path $projectNameFile -PathType Leaf) {
        try {
            $projectName = (Get-Content $projectNameFile -First 1 -ErrorAction SilentlyContinue).Trim()
            if (-not [string]::IsNullOrEmpty($projectName)) {
                return $projectName
            }
        } catch {
            # ignore
        }
    }

    return $null
}

function Find-TemplateFile {
    param(
        [Parameter(Mandatory=$true)]
        [string]$TemplateFilename,
        [Parameter(Mandatory=$true)]
        [string]$RepoRoot,
        [string]$UserTemplate = "",
        [string]$OmniSpecRoot = ""
    )

    $searchedPaths = @()

    if (-not [string]::IsNullOrEmpty($UserTemplate)) {
        $absTemplate = Normalize-Path -Path $UserTemplate -BasePath $RepoRoot
        $searchedPaths += $absTemplate
        if (Test-Path -Path $absTemplate -PathType Leaf) {
            return $absTemplate
        }
    }

    $projectName = Get-ProjectName -RepoRoot $RepoRoot
    if ($projectName) {
        $projectTemplate = Join-Path $RepoRoot (".infra/templates/$projectName/$TemplateFilename")
        $searchedPaths += $projectTemplate
        if (Test-Path -Path $projectTemplate -PathType Leaf) {
            return $projectTemplate
        }
    }

    $defaultTemplate = Join-Path $RepoRoot (".infra/templates/$TemplateFilename")
    $searchedPaths += $defaultTemplate
    if (Test-Path -Path $defaultTemplate -PathType Leaf) {
        return $defaultTemplate
    }

    $defaultDirTemplate = Join-Path $RepoRoot (".infra/templates/default/$TemplateFilename")
    $searchedPaths += $defaultDirTemplate
    if (Test-Path -Path $defaultDirTemplate -PathType Leaf) {
        return $defaultDirTemplate
    }

    if (-not [string]::IsNullOrEmpty($OmniSpecRoot)) {
        $systemDefaultDirTemplate = Join-Path $OmniSpecRoot ("specify/templates/default/$TemplateFilename")
        $searchedPaths += $systemDefaultDirTemplate
        if (Test-Path -Path $systemDefaultDirTemplate -PathType Leaf) {
            return $systemDefaultDirTemplate
        }

        $systemDefaultTemplate = Join-Path $OmniSpecRoot ("specify/templates/$TemplateFilename")
        $searchedPaths += $systemDefaultTemplate
        if (Test-Path -Path $systemDefaultTemplate -PathType Leaf) {
            return $systemDefaultTemplate
        }
    }

    Write-Error "Template file not found: $TemplateFilename"
    foreach ($p in $searchedPaths) {
        Write-Error "  - $p"
    }
    return $null
}

function Test-ShouldRequireConfirmation {
    param(
        [string]$Args = ""
    )

    if ([string]::IsNullOrEmpty($Args)) {
        $Args = $env:ARGUMENTS
    }

    if ($Args -match '--non-interactive' -or $Args -match '--yes') {
        return $false
    }

    if ($Args -match '--interactive\s+no') {
        return $false
    }

    if ($Args -match '--interactive\s+yes' -or $Args -match '--interactive(\s|$)') {
        return $true
    }

    return $false
}


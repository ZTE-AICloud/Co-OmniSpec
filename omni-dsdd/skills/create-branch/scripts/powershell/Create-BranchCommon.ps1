# create-branch 公共函数（由同目录脚本 dot-source）

function ConvertTo-CleanBranchName {
    param([string]$Name)
    return $Name.ToLower() -replace '[^a-z0-9]', '-' -replace '-{2,}', '-' -replace '^-', '' -replace '-$', ''
}

function Resolve-CreateBranchFeatureDirPath {
    param(
        [string]$FeatureDirInput,
        [string]$WorkingDir,
        [string]$ChangesDir
    )

    if (-not $FeatureDirInput -or $FeatureDirInput.Trim() -eq '') {
        return ''
    }

    $trimmed = $FeatureDirInput.Trim().TrimEnd('\', '/')
    if ([System.IO.Path]::IsPathRooted($trimmed)) {
        return $trimmed
    }

    if ($trimmed -match '^(changes[/\\].+)$') {
        return Join-Path $WorkingDir $trimmed
    }

    return Join-Path $ChangesDir $trimmed
}

function Write-CreateBranchOutputResults {
    param(
        [string]$BranchName,
        [string]$SpecFile,
        [string]$FeatureDir,
        [string]$HasGit,
        [bool]$Json
    )

    if ($Json) {
        [PSCustomObject]@{
            BRANCH_NAME = $BranchName
            SPEC_FILE   = $SpecFile
            FEATURE_DIR = $FeatureDir
            change_file = $SpecFile
            FEATURE_NUM = ''
            HAS_GIT     = $HasGit
        } | ConvertTo-Json -Compress
        return
    }

    Write-Output "BRANCH_NAME: $BranchName"
    Write-Output "SPEC_FILE: $SpecFile"
    Write-Output "FEATURE_DIR: $FeatureDir"
    Write-Output "change_file: $SpecFile"
    Write-Output "FEATURE_NUM: "
    Write-Output "HAS_GIT: $HasGit"
    if ($BranchName -and $BranchName.Trim() -ne '') {
        Write-Output "SPECIFY_FEATURE environment variable set to: $BranchName"
    }
}

function Test-CreateBranchWorkingDir {
    param([string]$WorkingDir)

    if (-not $WorkingDir -or $WorkingDir.Trim() -eq '') {
        Write-Error "Error: --working-dir is required"
        exit 1
    }
    if (-not (Test-Path -LiteralPath $WorkingDir -PathType Container)) {
        Write-Error "Error: --working-dir is not a directory: $WorkingDir"
        exit 1
    }
    return (Resolve-Path -LiteralPath $WorkingDir).Path
}

function Test-CreateBranchHasGit {
    param([string]$HasGit)

    if (-not $HasGit -or $HasGit.Trim() -eq '') {
        Write-Error "Error: --has-git is required (true or false)"
        exit 1
    }
    $normalized = $HasGit.Trim().ToLower()
    if ($normalized -notin @('true', 'false')) {
        Write-Error "Error: --has-git must be true or false"
        exit 1
    }
    return $normalized
}

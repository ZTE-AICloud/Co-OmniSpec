#!/usr/bin/env pwsh

<#
.SYNOPSIS
Search for keywords in specified path and return context (20 lines above/below) for each match.

.DESCRIPTION
Search for keywords in specified file or directory, supporting multiple keywords with OR logic.
Returns context (20 lines above/below) for each matching line in JSON format.

.PARAMETER Path
File or directory path to search

.PARAMETER Keywords
Keywords to search for (multiple keywords supported)

.EXAMPLE
.\load-private-specs.ps1 "doc/specs/design.md" "interface" "entity"
#>

param(
    [Parameter(Mandatory=$true, Position=0)]
    [string]$Path,
    
    [Parameter(Mandatory=$true, Position=1)]
    [string[]]$Keywords
)

$ErrorActionPreference = 'Stop'

# Check if path exists
if (-not (Test-Path -LiteralPath $Path)) {
    Write-Output "[]"
    exit 0
}

# Collect all matching results (using hashtable for deduplication)
$matchDict = @{}

foreach ($keyword in $Keywords) {
    if (Test-Path -LiteralPath $Path -PathType Container) {
        # Directory: recursively search all .md files
        $files = Get-ChildItem -Path $Path -Filter "*.md" -Recurse -File -ErrorAction SilentlyContinue
        foreach ($file in $files) {
            $content = Get-Content -LiteralPath $file.FullName -Encoding UTF8 -ErrorAction SilentlyContinue
            if ($null -eq $content) { continue }
            
            for ($i = 0; $i -lt $content.Length; $i++) {
                # Case-insensitive string matching (similar to grep -i)
                if ($content[$i] -ilike "*$keyword*") {
                    # Use string concatenation instead of interpolation to avoid colon parsing issues
                    $key = $file.FullName + ":" + ($i + 1)
                    if (-not $matchDict.ContainsKey($key)) {
                        $matchDict[$key] = @{
                            File = $file.FullName
                            Line = $i + 1
                        }
                    }
                }
            }
        }
    }
    else {
        # File: read and match directly
        $content = Get-Content -LiteralPath $Path -Encoding UTF8 -ErrorAction SilentlyContinue
        if ($null -eq $content) { continue }
        
        for ($i = 0; $i -lt $content.Length; $i++) {
            # Case-insensitive string matching (similar to grep -i)
            if ($content[$i] -ilike "*$keyword*") {
                # Use string concatenation instead of interpolation to avoid colon being parsed as drive identifier
                $key = $Path + ":" + ($i + 1)
                if (-not $matchDict.ContainsKey($key)) {
                    $matchDict[$key] = @{
                        File = $Path
                        Line = $i + 1
                    }
                }
            }
        }
    }
}

# Sort by file and line number
$uniqueMatches = $matchDict.Values | Sort-Object -Property File, Line

# Generate JSON output
Write-Output "["

$first = $true
foreach ($match in $uniqueMatches) {
    $file = $match.File
    $line = $match.Line
    
    # Read file content
    $content = Get-Content -LiteralPath $file -Encoding UTF8 -ErrorAction SilentlyContinue
    if ($null -eq $content) { continue }
    
    # Calculate range for 20 lines above/below (line numbers start at 1, array indices at 0)
    $lineIndex = $line - 1
    $startIndex = [Math]::Max(0, $lineIndex - 20)
    $endIndex = [Math]::Min($content.Length - 1, $lineIndex + 20)
    
    # Extract context lines
    $contextLines = $content[$startIndex..$endIndex]
    
    # Escape JSON special characters
    $escapedLines = @()
    foreach ($lineContent in $contextLines) {
        # Escape backslash, double quotes, remove carriage return and line feed
        $escaped = $lineContent -replace '\\', '\\\\' `
                               -replace '"', '\"' `
                               -replace "`r", '' `
                               -replace "`n", ''
        $escapedLines += $escaped
    }
    $context = $escapedLines -join '\n'
    
    # Output JSON object
    if (-not $first) {
        Write-Output ","
    }
    $first = $false
    
    $jsonLine = "  {`"line`":$line,`"context`":`"$context`"}"
    Write-Output $jsonLine
}

Write-Output ""
Write-Output "]"

#Requires -Version 5.1
<#
.SYNOPSIS
    Automates the packaging, GitHub release, and Scoop bucket synchronization for ProcessSentinel.

.DESCRIPTION
    Executes the post-compilation release pipeline:
    1. Validates preconditions (dist binaries exist, gh CLI authenticated, tag availability).
    2. Packages dist\ProcessSentinel into ProcessSentinel-v<Version>-windows-x64.zip.
    3. Computes the SHA-256 checksum.
    4. Updates processsentinel.json with the new version and checksum (enforcing CRLF & UTF-8 no-BOM).
    5. Commits and pushes the manifest to origin/main.
    6. Publishes the official GitHub release with the zip asset attached.
    7. Triggers the sync-processsentinel.yml workflow in Zunaid-Scoop-Bucket.
    8. Cleans up the local zip artifact.

.PARAMETER Version
    The new semantic version to release (e.g. "2.1.0"). Do not prefix with 'v'.

.PARAMETER Title
    The release title. Defaults to "ProcessSentinel v<Version>".

.PARAMETER Notes
    Markdown text for release notes.

.PARAMETER NotesFile
    Path to a markdown file containing release notes.

.PARAMETER BucketRepo
    Target Scoop bucket repository. Defaults to "zunaidFarouque/Zunaid-Scoop-Bucket".

.PARAMETER Force
    Bypasses the interactive confirmation prompt. (Required for non-interactive / agent automation).

.PARAMETER DryRun
    Simulates the process without pushing to GitHub or creating releases.

.EXAMPLE
    .\scripts\release.ps1 -Version "2.1.0" -Title "ProcessSentinel v2.1.0" -Notes "Added resource guards" -Force
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$Version,

    [Parameter(Mandatory = $false)]
    [string]$Title,

    [Parameter(Mandatory = $false)]
    [string]$Notes,

    [Parameter(Mandatory = $false)]
    [string]$NotesFile,

    [Parameter(Mandatory = $false)]
    [string]$BucketRepo = "zunaidFarouque/Zunaid-Scoop-Bucket",

    [Parameter(Mandatory = $false)]
    [switch]$Force,

    [Parameter(Mandatory = $false)]
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $repoRoot

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "  ProcessSentinel Automated Release Pipeline" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan

# ---------------------------------------------------------
# 1. Version Prompt & Pre-flight Checks
# ---------------------------------------------------------
if (-not $Version) {
    $Version = Read-Host "Enter release version (e.g. 2.1.0)"
}
$Version = $Version.Trim().TrimStart('v').TrimStart('V')
if (-not $Version) {
    Write-Error "A valid version string (e.g. 2.1.0) is required."
    exit 1
}

$tag = "v$Version"
if (-not $Title) {
    $Title = "ProcessSentinel $tag"
}

# Pre-flight Check: dist/ProcessSentinel binaries exist
$exePath = Join-Path $repoRoot "dist\ProcessSentinel\ProcessSentinel.exe"
if (-not (Test-Path $exePath)) {
    Write-Error "Pre-flight failed: Compiled binary not found at '$exePath'. Please run .\build-portable.bat before releasing."
    exit 1
}

# Pre-flight Check: GitHub CLI installed and authenticated
try {
    $ghAuth = gh auth status 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Pre-flight failed: GitHub CLI (gh) is not authenticated. Please run 'gh auth login'."
        exit 1
    }
} catch {
    Write-Error "Pre-flight failed: GitHub CLI (gh) was not found on PATH. Please install gh."
    exit 1
}

# Pre-flight Check: Tag does not already exist
$existingTag = git tag -l $tag
if ($existingTag) {
    Write-Error "Pre-flight failed: Tag '$tag' already exists locally. Use a higher version number."
    exit 1
}

# Confirmation Prompt
if (-not $Force -and -not $DryRun) {
    Write-Host "`nRelease Plan Summary:" -ForegroundColor Yellow
    Write-Host "  - Version:      $Version ($tag)"
    Write-Host "  - Title:        $Title"
    Write-Host "  - Binary:       $exePath"
    Write-Host "  - Bucket Repo:  $BucketRepo"
    $confirm = Read-Host "`nAre you sure you want to publish this release to GitHub and trigger Scoop bucket sync? (y/N)"
    if ($confirm -notmatch '^(y|yes)$') {
        Write-Host "Release cancelled by user." -ForegroundColor Gray
        exit 0
    }
}

# ---------------------------------------------------------
# 2. Package Zip Archive
# ---------------------------------------------------------
$zipName = "ProcessSentinel-$tag-windows-x64.zip"
$zipPath = Join-Path $repoRoot $zipName

Write-Host "`n[1/6] Packaging portable distribution into '$zipName'..." -ForegroundColor Green
if (Test-Path $zipPath) {
    Remove-Item $zipPath -Force
}

$distFolder = Join-Path $repoRoot "dist\ProcessSentinel\*"
Compress-Archive -Path $distFolder -DestinationPath $zipPath -Force

# ---------------------------------------------------------
# 3. Compute SHA-256 Checksum
# ---------------------------------------------------------
Write-Host "[2/6] Computing SHA-256 hash..." -ForegroundColor Green
$sha256 = (Get-FileHash -Path $zipPath -Algorithm SHA256).Hash.ToLower()
Write-Host "      SHA-256: $sha256" -ForegroundColor Cyan

# ---------------------------------------------------------
# 4. Update Canonical Scoop Manifest (processsentinel.json)
# ---------------------------------------------------------
Write-Host "[3/6] Updating canonical Scoop manifest (processsentinel.json)..." -ForegroundColor Green
$manifestPath = Join-Path $repoRoot "processsentinel.json"

if (-not (Test-Path $manifestPath)) {
    Write-Error "Canonical manifest '$manifestPath' not found."
    exit 1
}

$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$manifest.version = $Version
$manifest.architecture.'64bit'.url = "https://github.com/zunaidFarouque/ProcessSentinel/releases/download/$tag/$zipName"
$manifest.architecture.'64bit'.hash = $sha256

# Serialize with 4 spaces indentation and enforce CRLF without BOM (Scoop standards)
$jsonString = $manifest | ConvertTo-Json -Depth 10
# Replace LF with CRLF
$jsonString = $jsonString -replace "`r`n", "`n" -replace "`n", "`r`n"
# Ensure trailing CRLF
if (-not $jsonString.EndsWith("`r`n")) {
    $jsonString += "`r`n"
}

if (-not $DryRun) {
    # Write UTF-8 without BOM
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($manifestPath, $jsonString, $utf8NoBom)
} else {
    Write-Host "      [DryRun] Updated manifest in memory (skipped writing to disk)." -ForegroundColor Gray
}

# ---------------------------------------------------------
# 5. Commit & Push Updated Manifest
# ---------------------------------------------------------
Write-Host "[4/6] Committing and pushing updated manifest to main..." -ForegroundColor Green
if (-not $DryRun) {
    git add processsentinel.json
    git diff --staged --quiet
    if ($LASTEXITCODE -ne 0) {
        git commit -m "chore(release): Bump Scoop manifest to $tag"
        git push origin main
    } else {
        Write-Host "      Manifest already up to date on main." -ForegroundColor Gray
    }
} else {
    Write-Host "      [DryRun] Skipped git commit and push." -ForegroundColor Gray
}

# ---------------------------------------------------------
# 6. Publish GitHub Release
# ---------------------------------------------------------
Write-Host "[5/6] Publishing release '$tag' on GitHub..." -ForegroundColor Green
if (-not $DryRun) {
    $ghArgs = @("release", "create", $tag, $zipPath, "--title", $Title)
    if ($NotesFile -and (Test-Path $NotesFile)) {
        $ghArgs += @("--notes-file", $NotesFile)
    } elseif ($Notes) {
        $ghArgs += @("--notes", $Notes)
    } else {
        $ghArgs += @("--generate-notes")
    }

    & gh @ghArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to publish GitHub release."
        exit 1
    }
    Write-Host "      Release $tag successfully published!" -ForegroundColor Cyan
} else {
    Write-Host "      [DryRun] Skipped gh release create." -ForegroundColor Gray
}

# ---------------------------------------------------------
# 7. Trigger Bucket Sync & Cleanup
# ---------------------------------------------------------
Write-Host "[6/6] Triggering Scoop bucket sync in '$BucketRepo'..." -ForegroundColor Green
if (-not $DryRun) {
    try {
        gh workflow run sync-processsentinel.yml -R $BucketRepo
        Write-Host "      Successfully dispatched sync-processsentinel.yml to $BucketRepo!" -ForegroundColor Cyan
    } catch {
        Write-Warning "Failed to trigger workflow in $BucketRepo. You can manually run: gh workflow run sync-processsentinel.yml -R $BucketRepo"
    }
} else {
    Write-Host "      [DryRun] Skipped workflow dispatch." -ForegroundColor Gray
}

# Cleanup local temporary zip archive
if (Test-Path $zipPath) {
    Remove-Item $zipPath -Force
}

Write-Host "`n===================================================" -ForegroundColor Green
Write-Host "  ProcessSentinel $tag Release Complete!" -ForegroundColor Green
Write-Host "  URL: https://github.com/zunaidFarouque/ProcessSentinel/releases/tag/$tag" -ForegroundColor Green
Write-Host "===================================================" -ForegroundColor Green

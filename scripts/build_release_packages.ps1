param(
    [string]$Version = "2026.06.03"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$DistDir = Join-Path $ProjectRoot "dist"
$BuildRoot = Join-Path $ProjectRoot ".package-build"
$PackageRootName = "AI-for-medical-science"

if (Test-Path $BuildRoot) {
    Remove-Item -Recurse -Force $BuildRoot
}

New-Item -ItemType Directory -Force -Path $DistDir | Out-Null
New-Item -ItemType Directory -Force -Path $BuildRoot | Out-Null

$commonExcludeDirs = @(".git", ".venv", "__pycache__", ".package-build", "dist")
$commonExcludeFiles = @("*.pyc", ".env", "user_cases.json", "deleted_cases.json", "articles.json", "api_config.json", "api_config_history.json")

function Copy-PackageTree {
    param(
        [string]$Platform
    )

    $stage = Join-Path $BuildRoot $Platform
    $packageRoot = Join-Path $stage $PackageRootName
    New-Item -ItemType Directory -Force -Path $packageRoot | Out-Null

    robocopy $ProjectRoot $packageRoot /E /XD $commonExcludeDirs /XF $commonExcludeFiles | Out-Null
    if ($LASTEXITCODE -gt 7) {
        throw "robocopy failed with exit code $LASTEXITCODE"
    }

    $marker = Join-Path $packageRoot "PACKAGE_VERSION.txt"
    Set-Content -Path $marker -Value "AI for Medical Science $Version $Platform package" -Encoding UTF8
    return $packageRoot
}

$windowsRoot = Copy-PackageTree -Platform "windows"
$macRoot = Copy-PackageTree -Platform "macos"
$linuxRoot = Copy-PackageTree -Platform "linux"

$windowsZip = Join-Path $DistDir "AI-for-medical-science-windows.zip"
$macTar = Join-Path $DistDir "AI-for-medical-science-macos.tar.gz"
$linuxTar = Join-Path $DistDir "AI-for-medical-science-linux.tar.gz"

Remove-Item -Path @($windowsZip, $macTar, $linuxTar) -Force -ErrorAction SilentlyContinue

Compress-Archive -Path $windowsRoot -DestinationPath $windowsZip -Force
tar -czf $macTar -C (Split-Path $macRoot -Parent) $PackageRootName
tar -czf $linuxTar -C (Split-Path $linuxRoot -Parent) $PackageRootName

Write-Host "Created:"
Write-Host " - $windowsZip"
Write-Host " - $macTar"
Write-Host " - $linuxTar"

param(
    [string]$Version = "2026.06.03"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$DistDir = Join-Path $ProjectRoot "dist"
$BuildRoot = Join-Path $ProjectRoot ".package-build"
$PackageRootName = "AI-for-medical-science"
$WindowsLauncherExe = Join-Path $DistDir "AI-rare-disease-assistant.exe"

if (Test-Path $BuildRoot) {
    Remove-Item -Recurse -Force $BuildRoot
}

New-Item -ItemType Directory -Force -Path $DistDir | Out-Null
New-Item -ItemType Directory -Force -Path $BuildRoot | Out-Null

$commonExcludeDirs = @(".git", ".venv", "__pycache__", ".package-build", "dist")
$commonExcludeFiles = @("*.pyc", ".env", "user_cases.json", "deleted_cases.json", "articles.json", "api_config.json", "api_config_history.json", "ai-rare-disease-treatment-promo.mp4")

function Build-WindowsExeLauncher {
    $csc = @(
        "$env:WINDIR\Microsoft.NET\Framework64\v4.0.30319\csc.exe",
        "$env:WINDIR\Microsoft.NET\Framework\v4.0.30319\csc.exe"
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $csc) {
        Write-Warning "csc.exe was not found; Windows exe launcher was not built."
        return $null
    }

    $source = Join-Path $PSScriptRoot "windows_exe_launcher.cs"
    $icon = Join-Path $ProjectRoot "static\assets\app_icon.ico"
    $args = @(
        "/nologo",
        "/target:winexe",
        "/platform:anycpu",
        "/reference:System.Windows.Forms.dll",
        "/out:$WindowsLauncherExe"
    )
    if (Test-Path $icon) {
        $args += "/win32icon:$icon"
    }
    $args += $source
    & $csc @args
    if ($LASTEXITCODE -ne 0) {
        throw "csc.exe failed with exit code $LASTEXITCODE"
    }
    return $WindowsLauncherExe
}

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

$builtWindowsLauncher = Build-WindowsExeLauncher

$windowsRoot = Copy-PackageTree -Platform "windows"
$macRoot = Copy-PackageTree -Platform "macos"
$linuxRoot = Copy-PackageTree -Platform "linux"

if ($builtWindowsLauncher -and (Test-Path $builtWindowsLauncher)) {
    Copy-Item -Path $builtWindowsLauncher -Destination (Join-Path $windowsRoot "AI-rare-disease-assistant.exe") -Force
}

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
if (Test-Path $WindowsLauncherExe) {
    Write-Host " - $WindowsLauncherExe"
}

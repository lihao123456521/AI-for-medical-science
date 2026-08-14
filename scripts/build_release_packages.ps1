param(
    [string]$Version = "2026.08.15-v40"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$DistDir = Join-Path $ProjectRoot "dist"
$BuildRoot = Join-Path $ProjectRoot ".package-build"
$PackageRootName = "AI-for-medical-science"
$WindowsLauncherExe = Join-Path $DistDir "UroPUC.exe"

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
        # UroPUC.exe 是 Windows 发布包的必备交付物：csc 缺失必须直接失败，
        # 不允许生成没有 EXE 的 ZIP 继续发布。
        throw "csc.exe was not found; the Windows release requires UroPUC.exe to be built."
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
    if (-not (Test-Path $WindowsLauncherExe)) {
        throw "UroPUC.exe was not produced by csc.exe."
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

    # Runtime JSON names stay globally excluded. Only the audited public seed
    # directory is copied back into downloadable packages.
    $publicSeedSource = Join-Path $ProjectRoot "data\seed"
    $publicSeedTarget = Join-Path $packageRoot "data\seed"
    if (-not (Test-Path $publicSeedSource)) {
        throw "Public seed directory is missing: $publicSeedSource"
    }
    New-Item -ItemType Directory -Force -Path $publicSeedTarget | Out-Null
    Copy-Item -Path (Join-Path $publicSeedSource "*.json") -Destination $publicSeedTarget -Force

    $marker = Join-Path $packageRoot "PACKAGE_VERSION.txt"
    Set-Content -Path $marker -Value "UroPUC $Version $Platform package" -Encoding UTF8
    return $packageRoot
}

$builtWindowsLauncher = Build-WindowsExeLauncher

$windowsRoot = Copy-PackageTree -Platform "windows"
$macRoot = Copy-PackageTree -Platform "macos"
$linuxRoot = Copy-PackageTree -Platform "linux"

Copy-Item -Path $builtWindowsLauncher -Destination (Join-Path $windowsRoot "UroPUC.exe") -Force

# 硬门槛：Windows ZIP 根目录必须存在 UroPUC.exe，否则立即失败。
if (-not (Test-Path (Join-Path $windowsRoot "UroPUC.exe"))) {
    throw "Windows package root is missing UroPUC.exe; refusing to build the release ZIP."
}

$windowsZip = Join-Path $DistDir "UroPUC-windows.zip"
$macTar = Join-Path $DistDir "UroPUC-macos.tar.gz"
$linuxTar = Join-Path $DistDir "UroPUC-linux.tar.gz"

Remove-Item -Path @($windowsZip, $macTar, $linuxTar) -Force -ErrorAction SilentlyContinue

Compress-Archive -Path $windowsRoot -DestinationPath $windowsZip -Force
tar -czf $macTar -C (Split-Path $macRoot -Parent) $PackageRootName
tar -czf $linuxTar -C (Split-Path $linuxRoot -Parent) $PackageRootName

# ZIP 内容校验：确认压缩包内确实包含 UroPUC.exe。
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zipCheck = [IO.Compression.ZipFile]::OpenRead($windowsZip)
try {
    $zipNames = @($zipCheck.Entries | ForEach-Object { $_.FullName.Replace("\", "/") })
    if (($zipNames -notcontains "$PackageRootName/UroPUC.exe")) {
        throw "UroPUC.exe was not found inside $windowsZip."
    }
} finally {
    $zipCheck.Dispose()
}

Write-Host "Created:"
Write-Host " - $windowsZip"
Write-Host " - $macTar"
Write-Host " - $linuxTar"
Write-Host " - $WindowsLauncherExe"

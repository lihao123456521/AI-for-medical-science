param(
    [string]$SourceDir = (Resolve-Path (Join-Path $PSScriptRoot "..")),
    [string]$InstallDir = "D:\uscc_scc_flask_fixed",
    [string]$RuntimeDir = (Join-Path $env:USERPROFILE ".uscc_scc_flask_data"),
    [string]$BackupRoot = (Join-Path $env:USERPROFILE "AI-medical-backups"),
    [string]$DesktopShortcut = (Join-Path ([Environment]::GetFolderPath("Desktop")) "AI罕见病助手.lnk"),
    [switch]$SkipProcessStop,
    [switch]$SkipShortcut
)

$ErrorActionPreference = "Stop"
$source = [IO.Path]::GetFullPath($SourceDir)
$install = [IO.Path]::GetFullPath($InstallDir)
$runtime = [IO.Path]::GetFullPath($RuntimeDir)
$backupBase = [IO.Path]::GetFullPath($BackupRoot)

if (-not (Test-Path -LiteralPath $source -PathType Container)) {
    throw "Source directory does not exist: $source"
}
if ($source.TrimEnd('\') -eq $install.TrimEnd('\')) {
    throw "SourceDir and InstallDir must be different"
}

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupDir = Join-Path $backupBase $stamp
$installBackup = Join-Path $backupDir "application"
$runtimeBackup = Join-Path $backupDir "runtime-data"
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null

function Copy-Tree([string]$From, [string]$To) {
    if (-not (Test-Path -LiteralPath $From -PathType Container)) {
        New-Item -ItemType Directory -Force -Path $To | Out-Null
        return
    }
    New-Item -ItemType Directory -Force -Path $To | Out-Null
    & robocopy $From $To /E /R:1 /W:1 /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -gt 7) { throw "Backup copy failed with exit code $LASTEXITCODE" }
}

Copy-Tree $install $installBackup
Copy-Tree $runtime $runtimeBackup

if (-not $SkipProcessStop) {
    $escapedInstall = [Regex]::Escape($install.TrimEnd('\'))
    Get-CimInstance Win32_Process | Where-Object {
        $_.ProcessId -ne $PID -and $_.CommandLine -and $_.CommandLine -match $escapedInstall
    } | ForEach-Object {
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Milliseconds 800
}

New-Item -ItemType Directory -Force -Path $install | Out-Null
$excludeDirs = @(".git", ".venv", "__pycache__", ".package-build", "dist", "uploads", ".uscc_scc_flask_data")
$excludeFiles = @(
    ".env", "launcher.log", "api_config.json", "api_config_history.json",
    "user_cases.json", "deleted_cases.json", "articles.json", "case_tags.json",
    "library_state.json", "knowledge_digest.json"
)
$copyArgs = @($source, $install, "/MIR", "/R:2", "/W:1", "/NFL", "/NDL", "/NJH", "/NJS", "/NP", "/XD") + $excludeDirs + @("/XF") + $excludeFiles
& robocopy @copyArgs | Out-Null
if ($LASTEXITCODE -gt 7) { throw "Application deployment failed with exit code $LASTEXITCODE" }

if (-not $SkipShortcut) {
    $pythonw = Join-Path $install ".venv\Scripts\pythonw.exe"
    if (-not (Test-Path -LiteralPath $pythonw)) {
        $pythonw = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
    }
    if (-not $pythonw) { throw "pythonw.exe was not found for the desktop shortcut" }
    $shortcutParent = Split-Path -Parent $DesktopShortcut
    New-Item -ItemType Directory -Force -Path $shortcutParent | Out-Null
    $shell = New-Object -ComObject WScript.Shell
    $link = $shell.CreateShortcut($DesktopShortcut)
    $link.TargetPath = $pythonw
    $link.Arguments = '"' + (Join-Path $install "windows_launcher.pyw") + '"'
    $link.WorkingDirectory = $install
    $link.Description = "AI Rare Disease Assistant"
    $icon = Join-Path $install "static\assets\app_icon.ico"
    if (Test-Path -LiteralPath $icon) { $link.IconLocation = "$icon,0" }
    $link.Save()
}

[pscustomobject]@{
    source = $source
    install = $install
    runtime = $runtime
    install_backup = $installBackup
    runtime_backup = $runtimeBackup
    shortcut = $DesktopShortcut
} | ConvertTo-Json -Compress

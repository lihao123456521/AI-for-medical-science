param(
    [string]$Python = "python",
    [string]$DistPath = "dist/backend",
    [switch]$SkipDeps
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Push-Location $ProjectRoot
try {
    if (-not $SkipDeps) {
        Write-Host "[backend] Installing runtime deps + PyInstaller..."
        & $Python -m pip install --disable-pip-version-check -r requirements.txt "pyinstaller>=6.6"
        if ($LASTEXITCODE -ne 0) { throw "pip install failed with exit code $LASTEXITCODE" }
    }

    Write-Host "[backend] Building UroPUCBackend (onedir)..."
    & $Python -m PyInstaller --noconfirm --clean `
        --distpath $DistPath `
        --workpath "$DistPath/.work" `
        packaging/UroPUCBackend.spec
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE" }

    $exeName = if ($IsWindows -or $env:OS -eq "Windows_NT") { "UroPUCBackend.exe" } else { "UroPUCBackend" }
    $backendExe = Join-Path $ProjectRoot "$DistPath/UroPUCBackend/$exeName"
    if (-not (Test-Path $backendExe)) { throw "Backend executable was not produced: $backendExe" }

    # 私密数据绝不允许进入产物（data/seed 下的公开种子除外）
    $bundle = Get-ChildItem (Join-Path $ProjectRoot "$DistPath/UroPUCBackend") -Recurse -File
    $seedDir = (Join-Path $ProjectRoot "$DistPath/UroPUCBackend/_internal/data/seed").Replace('/', [IO.Path]::DirectorySeparatorChar)
    $privateHits = $bundle | Where-Object {
        $_.Name -in @("api_config.json", "api_config_history.json", ".env", "deleted_cases.json") -or
        ($_.Name -in @("user_cases.json", "articles.json") -and -not $_.FullName.StartsWith($seedDir))
    }
    if ($privateHits) {
        throw "Private data leaked into backend bundle: $($privateHits.FullName -join ', ')"
    }

    Write-Host "[backend] Build OK: $backendExe ($($bundle.Count) files)"
    return $backendExe
}
finally {
    Pop-Location
}

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$appName = "ClassTeacherManager"
$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $python = "python"
}

$runningInstances = @(Get-Process -Name $appName -ErrorAction SilentlyContinue)
if ($runningInstances.Count -gt 0) {
    $processIds = $runningInstances.Id -join ", "
    throw "Please close the running $appName application before packaging. Process ID: $processIds"
}

$previousErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& $python -m PyInstaller --version 2>$null | Out-Null
$pyInstallerInstalled = $LASTEXITCODE -eq 0
$ErrorActionPreference = $previousErrorActionPreference

if (-not $pyInstallerInstalled) {
    & $python -m pip install "PyInstaller>=6.0"
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to install PyInstaller."
    }
}

$resources = Join-Path $root "resources"
$dist = Join-Path $root "dist-python"
$work = Join-Path $root "build\pyinstaller"
$version = (& $python -c "import sys; sys.path.insert(0, r'$root'); from config import APP_VERSION; print(APP_VERSION)").Trim()
$versionFile = Join-Path $root "build\windows_version_info.txt"
$iconFile = Join-Path $resources "app.ico"
$pythonPath = (Get-Command $python).Source
$pythonDirectory = Split-Path -Parent $pythonPath

& $python (Join-Path $root "utils\write_windows_version_info.py") $versionFile
if ($LASTEXITCODE -ne 0) {
    throw "Unable to create Windows version metadata."
}

$originalPath = $env:PATH
$cleanPath = @(
    $pythonDirectory,
    (Join-Path $env:SystemRoot "System32"),
    $env:SystemRoot,
    (Join-Path $env:SystemRoot "System32\Wbem")
) | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -Unique

try {
    # Keep unrelated developer tools out of DLL discovery. In particular, a
    # Poppler ICU DLL on PATH is binary-incompatible with the Windows Qt build.
    $env:PATH = $cleanPath -join [IO.Path]::PathSeparator
    & $python -m PyInstaller `
        --noconfirm `
        --clean `
        --windowed `
        --onedir `
        --name $appName `
        --icon $iconFile `
        --version-file $versionFile `
        --add-data "$resources;resources" `
        --distpath $dist `
        --workpath $work `
        --specpath $work `
        (Join-Path $root "main.py")
    $pyInstallerExitCode = $LASTEXITCODE
} finally {
    $env:PATH = $originalPath
}

if ($pyInstallerExitCode -ne 0) {
    throw "Python exe build failed with exit code $pyInstallerExitCode"
}

$appOutputDir = Join-Path $dist $appName
$internalDir = Join-Path $appOutputDir "_internal"
$unexpectedIcuFiles = @(Get-ChildItem -LiteralPath $internalDir -Filter "icu*.dll" -File -ErrorAction SilentlyContinue)
if ($unexpectedIcuFiles.Count -gt 0) {
    $unexpectedNames = $unexpectedIcuFiles.Name -join ", "
    throw "Unexpected private ICU runtime collected from PATH: $unexpectedNames"
}

$installGuide = Join-Path $root "docs\安装与启动说明.txt"
Copy-Item -LiteralPath $installGuide -Destination (Join-Path $appOutputDir "安装与启动说明.txt") -Force

$exePath = Join-Path $appOutputDir "$appName.exe"
$releaseZip = Join-Path $dist "$appName-v$version-win64.zip"
if (Test-Path $releaseZip) {
    Remove-Item -LiteralPath $releaseZip -Force
}
Compress-Archive -Path (Join-Path $dist $appName) -DestinationPath $releaseZip -CompressionLevel Optimal
$checksumPath = "$releaseZip.sha256"
$releaseHash = (Get-FileHash -LiteralPath $releaseZip -Algorithm SHA256).Hash
Set-Content -LiteralPath $checksumPath -Value "$releaseHash  $([IO.Path]::GetFileName($releaseZip))" -Encoding ascii

Write-Host ("Created EXE: " + $exePath)
Write-Host ("Created package: " + $releaseZip)
Write-Host ("Created checksum: " + $checksumPath)

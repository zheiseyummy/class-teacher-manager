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

& $python -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --onedir `
    --name $appName `
    --add-data "$resources;resources" `
    --distpath $dist `
    --workpath $work `
    --specpath $work `
    (Join-Path $root "main.py")

if ($LASTEXITCODE -ne 0) {
    throw "Python exe build failed with exit code $LASTEXITCODE"
}

Write-Host ("Created: " + (Join-Path $dist "$appName\$appName.exe"))

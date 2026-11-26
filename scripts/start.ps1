param([switch]$Desktop, [string]$Profile = 'default')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    if (!(Test-Path '.venv/Scripts/python.exe') -or !(Test-Path 'frontend/dist/index.html')) { throw 'Esegui prima scripts/bootstrap.ps1.' }
    $env:PYTHONPATH = Join-Path $projectRoot 'backend'
    if ($Desktop) {
        $env:DEEPSTUDY_ROOT = $projectRoot
        $env:DEEPSTUDY_PROFILE = $Profile
        & './src-tauri/target/debug/deepstudy.exe'
    } else {
        & './.venv/Scripts/python.exe' -m deepstudy.server --profile $Profile
    }
    if ($LASTEXITCODE -ne 0) { throw "Avvio fallito (codice $LASTEXITCODE)." }
} finally { Pop-Location }

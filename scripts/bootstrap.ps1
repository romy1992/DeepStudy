$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Creazione ambiente Python fallita.' }
    & ./.venv/Scripts/python.exe -m pip install -r backend/requirements.lock
    if ($LASTEXITCODE -ne 0) { throw 'Installazione Python fallita.' }
    npm ci
    if ($LASTEXITCODE -ne 0) { throw 'Installazione frontend fallita.' }
    npm run desktop:build
    if ($LASTEXITCODE -ne 0) { throw 'Build fallita.' }
} finally { Pop-Location }

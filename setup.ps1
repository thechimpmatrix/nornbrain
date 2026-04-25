#Requires -Version 5.1
<#
.SYNOPSIS
    NORNBRAIN first-time environment setup (Windows PowerShell).
.DESCRIPTION
    Creates a Python virtual environment, installs dependencies, and
    sets up .env from .env.example. Does NOT build the openc2e engine;
    see https://github.com/thechimpmatrix/openc2e-nb for engine build instructions.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "=== NORNBRAIN Setup ===" -ForegroundColor Cyan
Write-Host ""

# --- Python version check ---
$pythonExe = $null
foreach ($candidate in @("python", "python3", "py")) {
    try {
        $null = & $candidate --version 2>&1
        $pythonExe = $candidate
        break
    } catch { }
}

if (-not $pythonExe) {
    Write-Error "Python is not on PATH. Install Python 3.11 or later from https://www.python.org/downloads/"
    exit 1
}

$versionOutput = & $pythonExe --version 2>&1
$versionString = ($versionOutput -replace "Python ", "").Trim()
$versionParts = $versionString.Split(".")
$major = [int]$versionParts[0]
$minor = [int]$versionParts[1]

if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 11)) {
    Write-Error "Python 3.11 or later is required. Found: Python $versionString"
    exit 1
}

Write-Host "Python $versionString found." -ForegroundColor Green

# --- Virtual environment ---
if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment at .venv\ ..."
    & $pythonExe -m venv .venv
} else {
    Write-Host "Virtual environment already exists at .venv\"
}

# Activate
$activateScript = ".venv\Scripts\Activate.ps1"
if (-not (Test-Path $activateScript)) {
    Write-Error "Could not find $activateScript. Virtual environment may be corrupted."
    exit 1
}
& $activateScript

Write-Host "Installing dependencies from requirements.txt ..."
pip install --upgrade pip --quiet
pip install -r requirements.txt

# --- Environment file ---
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host ""
    Write-Host "Created .env from .env.example."
    Write-Host "Edit .env and set C3_DATA_PATH to your Creatures 3 game data directory."
}

# --- Verify import ---
Write-Host ""
Write-Host "Verifying core imports ..."
& python -c "import torch; import ncps; print(f'  torch {torch.__version__}, ncps OK')"

Write-Host ""
Write-Host "=== Setup complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Edit .env and set C3_DATA_PATH to your Creatures 3 data folder."
Write-Host "  2. Build the openc2e engine (separate repo: openc2e-nb) - see https://github.com/thechimpmatrix/openc2e-nb."
Write-Host "  3. Read README.md for the full quickstart."
Write-Host ""
Write-Host "To activate the environment in future sessions:"
Write-Host "  .venv\Scripts\Activate.ps1"

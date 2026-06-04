#Requires -RunAsAdministrator
<#
.SYNOPSIS
  One-time setup on a Windows VPS: Python venv + dependencies.

  Run in PowerShell (Admin) from the project folder:
    Set-ExecutionPolicy -Scope Process Bypass
    .\deploy\setup_vps.ps1
#>

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "=== BrahMos Bot VPS setup ===" -ForegroundColor Cyan
Write-Host "Project: $ProjectRoot"

# 1) Python
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "Python not found. Install Python 3.11+ from https://www.python.org/downloads/" -ForegroundColor Red
    Write-Host "Check 'Add python.exe to PATH' during install, then re-run this script."
    exit 1
}
Write-Host "Python: $($python.Source)"

# 2) venv + pip
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    python -m venv .venv
}
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\pip.exe install -r requirements.txt

# 3) .env
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env — edit MT5_LOGIN, MT5_PASSWORD, MT5_SERVER before starting." -ForegroundColor Yellow
}

# 4) logs folder
New-Item -ItemType Directory -Force -Path "logs" | Out-Null

Write-Host ""
Write-Host "Setup complete. Next steps:" -ForegroundColor Green
Write-Host "  1. Install XM MT5, login once, enable Algo Trading"
Write-Host "  2. Edit .env with your credentials"
Write-Host "  3. Run: .\deploy\install_task.ps1   (auto-start on boot)"
Write-Host "  Or test manually: .\deploy\start_bot.ps1"

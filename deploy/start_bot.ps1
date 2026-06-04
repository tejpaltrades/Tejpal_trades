<#
.SYNOPSIS
  Launch bot (starts MT5 first, then Python). Used by Task Scheduler on VPS.
#>

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

# Load MT5_TERMINAL_PATH from .env for start_mt5.ps1
$envFile = Join-Path $ProjectRoot ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*MT5_TERMINAL_PATH=(.+)$') {
            $env:MT5_TERMINAL_PATH = $matches[1].Trim()
        }
    }
}

& "$PSScriptRoot\start_mt5.ps1"

$python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Error "Run deploy\setup_vps.ps1 first"
}

Write-Host "Starting BrahMos bot..."
& $python (Join-Path $ProjectRoot "bot.py")

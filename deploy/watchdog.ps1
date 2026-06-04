<#
.SYNOPSIS
  Start the bot if it is not already running. Used by Task Scheduler every minute.
#>

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$botScript = Join-Path $ProjectRoot "bot.py"

if (-not (Test-Path $python)) {
    Write-Warning "Venv missing — run deploy\setup_vps.ps1 or deploy\deploy_from_git.ps1 first"
    exit 1
}

if (-not (Test-Path (Join-Path $ProjectRoot ".env"))) {
    Write-Warning ".env missing — copy .env.example to .env and add MT5 credentials"
    exit 1
}

$running = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -and $_.CommandLine -like "*$botScript*" }

if ($running) {
    exit 0
}

$startBot = Join-Path $PSScriptRoot "start_bot.ps1"
Start-Process -FilePath "powershell.exe" `
    -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$startBot`"" `
    -WorkingDirectory $ProjectRoot `
    -WindowStyle Hidden

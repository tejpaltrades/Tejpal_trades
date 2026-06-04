#Requires -RunAsAdministrator
<#
.SYNOPSIS
  Clone or update the bot from GitHub/GitLab, install Python deps, optional 24/7 task.

.PARAMETER RepoUrl
  HTTPS git URL, e.g. https://github.com/you/Tejpal_trades.git

.PARAMETER InstallPath
  Folder on the VPS (default C:\Tejpal_trades)

.PARAMETER Branch
  Git branch to clone (default main)

.PARAMETER AutoStart
  Also register the BrahMosGoldBot scheduled task (24/7)

.EXAMPLE
  Set-ExecutionPolicy -Scope Process Bypass
  .\deploy\deploy_from_git.ps1 -RepoUrl "https://github.com/you/Tejpal_trades.git" -AutoStart
#>

param(
    [Parameter(Mandatory = $true)]
    [string]$RepoUrl,

    [string]$InstallPath = "C:\Tejpal_trades",

    [string]$Branch = "main",

    [switch]$AutoStart
)

$ErrorActionPreference = "Stop"

Write-Host "=== BrahMos deploy from Git ===" -ForegroundColor Cyan

$git = Get-Command git -ErrorAction SilentlyContinue
if (-not $git) {
    Write-Host "Git not found. Install from https://git-scm.com/download/win then re-run." -ForegroundColor Red
    exit 1
}

$parent = Split-Path -Parent $InstallPath
if ($parent -and -not (Test-Path $parent)) {
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
}

if (Test-Path (Join-Path $InstallPath ".git")) {
    Write-Host "Updating existing repo at $InstallPath"
    Set-Location $InstallPath
    git fetch origin
    git checkout $Branch
    git pull origin $Branch
}
elseif (Test-Path $InstallPath) {
    Write-Host "Folder exists but is not a git repo: $InstallPath" -ForegroundColor Red
    Write-Host "Use another InstallPath or remove/rename that folder."
    exit 1
}
else {
    Write-Host "Cloning $RepoUrl -> $InstallPath (branch $Branch)"
    git clone -b $Branch $RepoUrl $InstallPath
    Set-Location $InstallPath
}

& "$InstallPath\deploy\setup_vps.ps1"

if (-not (Test-Path "$InstallPath\.env")) {
    Write-Host ""
    Write-Host "IMPORTANT: Edit $InstallPath\.env with MT5 login, password, server." -ForegroundColor Yellow
    Write-Host "  (.env is not in Git — you type secrets once on the VPS.)"
    Write-Host "  notepad $InstallPath\.env"
}

if ($AutoStart) {
    if (-not (Test-Path "$InstallPath\.env")) {
        Write-Host "Skipping AutoStart until .env exists." -ForegroundColor Yellow
    }
    else {
        & "$InstallPath\deploy\install_task.ps1"
        Start-ScheduledTask -TaskName BrahMosGoldBot
        Write-Host "Bot task started." -ForegroundColor Green
    }
}
else {
    Write-Host ""
    Write-Host "When .env is ready, test with:" -ForegroundColor Green
    Write-Host "  cd $InstallPath"
    Write-Host "  .\deploy\start_bot.ps1"
    Write-Host ""
    Write-Host "Then enable 24/7:"
    Write-Host "  .\deploy\install_task.ps1"
    Write-Host "  Start-ScheduledTask -TaskName BrahMosGoldBot"
}

Write-Host ""
Write-Host "Done. Install path: $InstallPath" -ForegroundColor Green

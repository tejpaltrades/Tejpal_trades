<#
.SYNOPSIS
  Start XM MT5 if not already running (needed before Python bot connects).
#>

$ErrorActionPreference = "Stop"

$paths = @(
    $env:MT5_TERMINAL_PATH,
    "C:\Program Files\MetaTrader 5\terminal64.exe",
    "C:\Program Files\XM MT5\terminal64.exe",
    "$env:APPDATA\MetaQuotes\Terminal\*\terminal64.exe"
)

$exe = $null
foreach ($p in $paths) {
    if (-not $p) { continue }
    if ($p -like "*`*") {
        $found = Get-ChildItem -Path ($p -replace '\\terminal64.exe$','') -Filter terminal64.exe -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($found) { $exe = $found.FullName; break }
    }
    elseif (Test-Path $p) {
        $exe = $p
        break
    }
}

if (-not $exe) {
    Write-Warning "MT5 terminal64.exe not found. Install XM MT5 or set MT5_TERMINAL_PATH in .env"
    exit 1
}

$proc = Get-Process -Name "terminal64" -ErrorAction SilentlyContinue
if ($proc) {
    Write-Host "MT5 already running (PID $($proc.Id))"
    exit 0
}

Write-Host "Starting MT5: $exe"
Start-Process -FilePath $exe
Start-Sleep -Seconds 45
Write-Host "MT5 started — wait for login if first run"

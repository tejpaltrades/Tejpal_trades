#Requires -RunAsAdministrator
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$watchdog = Join-Path $PSScriptRoot "watchdog.ps1"
$TaskName = "BrahMosGoldBot"
if (-not (Test-Path $watchdog)) { Write-Error "Missing $watchdog" }
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$watchdog`"" -WorkingDirectory $ProjectRoot
$bootTrigger = New-ScheduledTaskTrigger -AtStartup
$bootTrigger.Delay = "PT2M"
$repeatTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 1) -RepetitionDuration ([TimeSpan]::MaxValue)
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 0)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger @($bootTrigger, $repeatTrigger) -Settings $settings -Principal $principal -Force | Out-Null
Write-Host "Scheduled task '$TaskName' installed."

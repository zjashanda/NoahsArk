#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Repair a NoahsArk Node Agent scheduled task so it reconnects forever.

.DESCRIPTION
    The legacy one-click installer created "NoahsArkNodeAgent" with the Windows
    default execution time limit (72 hours).  Task Scheduler then kills the
    long-running agent after three days, and because no restart-on-failure was
    configured the node stays offline until someone logs in manually.

    This script is idempotent:
      * resolves run-agent.bat under -InstallDir;
      * creates run-agent-loop.bat, which restarts Python when it exits;
      * points the task at the loop wrapper;
      * sets ExecutionTimeLimit=PT0S and RestartOnFailure=1 minute x 999;
      * starts the task and prints the resulting state.

    It never reads or prints the node token.

.PARAMETER InstallDir
    Directory containing run-agent.bat and the agent code.
    Use C:\Temp\node_agent for the legacy layout, or the current installer
    default C:\ProgramData\NoahsArk\Node.

.PARAMETER TaskName
    Scheduled task name.  Defaults to NoahsArkNodeAgent.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\repair-node-agent-task.ps1 `
        -InstallDir C:\Temp\node_agent
#>

[CmdletBinding()]
param(
    [string]$InstallDir = 'C:\ProgramData\NoahsArk\Node',
    [string]$TaskName = 'NoahsArkNodeAgent'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Step {
    param([string]$Message)
    Write-Host "[repair-node-agent] $Message"
}

$install = (Resolve-Path -LiteralPath $InstallDir).Path
$bat = Join-Path $install 'run-agent.bat'
$loop = Join-Path $install 'run-agent-loop.bat'
$log = Join-Path $install 'agent.log'

if (-not (Test-Path -LiteralPath $bat)) {
    throw "run-agent.bat not found under $install"
}

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($null -eq $task) {
    throw "scheduled task '$TaskName' does not exist; run the node installer first"
}

if ((Test-Path -LiteralPath $log) -and ((Get-Item -LiteralPath $log).Length -gt 5MB)) {
    Move-Item -LiteralPath $log -Destination "$log.1" -Force
}

$loopContent = @"
@echo off
:loop
call "$bat" >> "$log" 2>&1
timeout /t 5 /nobreak >nul
goto loop
"@
Set-Content -LiteralPath $loop -Value $loopContent -Encoding ASCII
Write-Step "loop wrapper: $loop"

$action = New-ScheduledTaskAction -Execute $loop -WorkingDirectory $install
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 1)

Set-ScheduledTask -TaskName $TaskName -Action $action -Settings $settings | Out-Null
Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 3

$state = (Get-ScheduledTask -TaskName $TaskName).State
$info = Get-ScheduledTaskInfo -TaskName $TaskName
$running = @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -match 'noahsark_node' })

Write-Step "task state: $state"
Write-Step "last run: $($info.LastRunTime); last result: $($info.LastTaskResult)"
Write-Step "agent processes: $($running.Count)"

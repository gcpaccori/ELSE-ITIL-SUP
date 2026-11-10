# QA only: outbound Windows NuGet dispatcher. Requires current authorized
# Windows user session and preexisting outbound SSH to elsecluster5.
$ErrorActionPreference = "Stop"
$task = "ELSE-ITIL-QA-OutboundNuGet"
$root = "C:\Temp\ELSE_ITIL_DYNAMIC_NUGET_20261109"
$worker = Join-Path $root "qa\qa_outbound_worker_windows.py"
$python = "C:\Program Files\Python311\python.exe"
if (!(Test-Path $worker) -or !(Test-Path $python)) {
  throw "QA_WORKER_DEPENDENCIES_NOT_PRESENT"
}
$identity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$action = New-ScheduledTaskAction -Execute $python -Argument ('"' + $worker + '" --once') -WorkingDirectory (Join-Path $root "qa")
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 1) -RepetitionDuration (New-TimeSpan -Days 365)
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 10) -StartWhenAvailable
$principal = New-ScheduledTaskPrincipal -UserId $identity -LogonType S4U -RunLevel Limited
Register-ScheduledTask -TaskName $task -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
Write-Output ("QA_WORKER_TASK_REGISTERED=" + $task)
Write-Output ("QA_WORKER_RUN_AS=" + $identity)
Write-Output ("QA_WORKER_TRIGGER_MINUTES=1")

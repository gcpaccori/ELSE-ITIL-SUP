$ErrorActionPreference='Stop'
$TaskName='ELSE_ITIL_BETA_FRESH_OT_QA'
$Root='C:\Temp\ELSE_ITIL_BETA_FRESH_QA_20261110'
$Wrapper=$Root+'\run-worker.cmd'
if(-not (Test-Path $Wrapper)){throw 'QA_WORKER_WRAPPER_NOT_FOUND'}
$CurrentUser=[Security.Principal.WindowsIdentity]::GetCurrent().Name
$Action=New-ScheduledTaskAction -Execute 'C:\Windows\System32\cmd.exe' -Argument ('/c "'+$Wrapper+'"') -WorkingDirectory 'C:\Temp\ELSE_ITIL_FEB100_QA_20261110\qa'
$Trigger=New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 5) -RepetitionDuration (New-TimeSpan -Days 365)
$Principal=New-ScheduledTaskPrincipal -UserId $CurrentUser -LogonType S4U -RunLevel Limited
$Settings=New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 3) -StartWhenAvailable
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings -Force | Out-Null
$Registered=Get-ScheduledTask -TaskName $TaskName
Write-Output ('QA_TASK_REGISTERED='+$Registered.TaskName)
Write-Output ('QA_TASK_STATE='+$Registered.State)
Write-Output ('QA_TASK_USER='+$Registered.Principal.UserId)
Write-Output ('QA_TASK_LOGON='+$Registered.Principal.LogonType)

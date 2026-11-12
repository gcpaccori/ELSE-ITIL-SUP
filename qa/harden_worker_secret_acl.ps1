$ErrorActionPreference='Stop'
$Path='C:\Temp\ELSE_ITIL_BETA_FRESH_QA_20261110\worker_hmac.private'
$Account=[Security.Principal.WindowsIdentity]::GetCurrent().Name
if(-not (Test-Path $Path)){throw 'QA_SECRET_MISSING'}
& icacls.exe $Path '/inheritance:r' '/grant:r' "$($Account):(F)" 'NT AUTHORITY\SYSTEM:(F)' 'BUILTIN\Administrators:(F)'
if($LASTEXITCODE -ne 0){throw 'ICACLS_FAILED'}
& icacls.exe $Path

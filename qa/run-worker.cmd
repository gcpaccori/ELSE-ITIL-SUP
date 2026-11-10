@echo off
"C:\Program Files\Python311\python.exe" "C:\Temp\ELSE_ITIL_FEB100_QA_20261110\qa\qa_v1beta_fresh_ot_windows.py" --once >> "C:\Temp\ELSE_ITIL_BETA_FRESH_QA_20261110\scheduled.stdout.log" 2>> "C:\Temp\ELSE_ITIL_BETA_FRESH_QA_20261110\scheduled.stderr.log"
exit /b %errorlevel%

@echo off
cd /d "%~dp0"
echo Verify the latest full archive in a NEW scratch folder. Live data is not replaced.
"python\python.exe" -B backup_tools.py restore
set "CAMPUS_RESTORE_EXIT=%ERRORLEVEL%"
pause
exit /b %CAMPUS_RESTORE_EXIT%

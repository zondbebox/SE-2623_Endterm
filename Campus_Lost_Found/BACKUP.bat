@echo off
cd /d "%~dp0"
echo Full data archive: SQLite databases and private photos. Session keys are excluded.
echo Pause changes in the app while this backup runs.
"python\python.exe" -B backup_tools.py backup
set "CAMPUS_BACKUP_EXIT=%ERRORLEVEL%"
pause
exit /b %CAMPUS_BACKUP_EXIT%

@echo off
cd /d "%~dp0"
"python\python.exe" -B -m unittest discover -s backend -p test_backend.py -v
if errorlevel 1 goto finished
"python\python.exe" -B test_app.py
if errorlevel 1 goto finished
"python\python.exe" -B test_media.py
if errorlevel 1 goto finished
"python\python.exe" -B test_stage2_core.py
if errorlevel 1 goto finished
"python\python.exe" -B test_analytics.py
if errorlevel 1 goto finished
"python\python.exe" -B test_admin_panel.py
if errorlevel 1 goto finished
"python\python.exe" -B test_stage2_features.py
if errorlevel 1 goto finished
"python\python.exe" -B test_backup_full.py
:finished
set "CAMPUS_TEST_EXIT=%ERRORLEVEL%"
pause
exit /b %CAMPUS_TEST_EXIT%

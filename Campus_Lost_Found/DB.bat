@echo off
cd /d "%~dp0"
"python\python.exe" -m backend.manage %*

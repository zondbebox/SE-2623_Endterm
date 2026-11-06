@echo off
cd /d "%~dp0"
echo Open http://127.0.0.1:5055 in your browser.
echo Keep this window open. Press Ctrl+C to stop.
"python\python.exe" app.py
pause

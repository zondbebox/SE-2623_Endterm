@echo off
cd /d "%~dp0"
echo SQLite database inspector: http://127.0.0.1:8088
echo Read-only mode. Keep this window open during inspection.
"python\python.exe" -m sqlite_web.sqlite_web data\campus.sqlite3 --host 127.0.0.1 --port 8088 --read-only --foreign-keys --no-browser
pause

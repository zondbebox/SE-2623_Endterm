@echo off
rem Start Campus Lost & Found with Microsoft sign-in (Astana IT University Entra tenant).
rem The tenant and client IDs are not secrets. The client secret is asked for every time,
rem kept only in this window's memory and never written to a file.
cd /d "%~dp0"
set "CAMPUS_ENTRA_TENANT_ID=158f15f3-83e0-4906-824c-69bdc50d9d61"
set "CAMPUS_ENTRA_CLIENT_ID=bcaef12d-93f2-4b47-8e36-a4194f4402cd"
set "CAMPUS_ENTRA_REDIRECT_URI=http://localhost:5055/auth/microsoft/callback"
echo Paste the client secret VALUE from Entra (input is hidden), then press Enter.
for /f "usebackq delims=" %%s in (`powershell -NoProfile -Command "$s = Read-Host 'Client secret' -AsSecureString; [Runtime.InteropServices.Marshal]::PtrToStringBSTR([Runtime.InteropServices.Marshal]::SecureStringToBSTR($s))"`) do set "CAMPUS_ENTRA_CLIENT_SECRET=%%s"
if not defined CAMPUS_ENTRA_CLIENT_SECRET (
    echo No secret entered. Use START.bat for local sign-in only.
    pause
    exit /b 1
)
echo.
echo Open http://localhost:5055/login  (use localhost, not 127.0.0.1)
echo and click "Sign in with Microsoft (university account)".
echo Keep this window open. Press Ctrl+C to stop.
"python\python.exe" app.py
set "CAMPUS_ENTRA_CLIENT_SECRET="
pause

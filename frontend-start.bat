@echo off
setlocal

cd /d "%~dp0"

curl --silent --fail "http://127.0.0.1:8000" >nul 2>&1
if errorlevel 1 (
    start "Text-to-3D Backend" /d "%~dp0backend" "%~dp0backend\venv\Scripts\python.exe" -m uvicorn main:app --host 127.0.0.1 --port 8000
)

set /a ATTEMPTS=0
:wait_for_backend
curl --silent --fail "http://127.0.0.1:8000" >nul 2>&1
if not errorlevel 1 goto backend_ready
set /a ATTEMPTS+=1
if %ATTEMPTS% GEQ 30 (
    echo Backend did not become ready at http://127.0.0.1:8000.
    exit /b 1
)
timeout /t 1 /nobreak >nul
goto wait_for_backend

:backend_ready
cd /d "%~dp0frontend"
call npm run dev -- --host 127.0.0.1 --port 5173 --open
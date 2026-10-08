@echo off
setlocal

cd /d "%~dp0"

if not exist "backend\venv\Scripts\python.exe" (
    py -m venv backend\venv
)

call "backend\venv\Scripts\activate.bat"
python -m pip install --upgrade pip
if errorlevel 1 exit /b 1
python -m pip install -r backend\requirements.txt
if errorlevel 1 exit /b 1

pushd frontend
if not exist "node_modules\.bin\vite.cmd" (
    call npm install
    if errorlevel 1 (
        popd
        exit /b 1
    )
)
call npm run build
if errorlevel 1 (
    popd
    exit /b 1
)
popd

start "Text-to-3D Backend" /d "%~dp0backend" "%~dp0backend\venv\Scripts\python.exe" -m uvicorn main:app --host 127.0.0.1 --port 8000

set "APP_URL=http://127.0.0.1:8000"
set /a ATTEMPTS=0
:wait_for_backend
curl --silent --fail "%APP_URL%" >nul 2>&1
if not errorlevel 1 goto backend_ready
set /a ATTEMPTS+=1
if %ATTEMPTS% GEQ 30 (
    echo Backend did not become ready at %APP_URL%.
    exit /b 1
)
timeout /t 1 /nobreak >nul
goto wait_for_backend

:backend_ready
start "" "http://127.0.0.1:8000"
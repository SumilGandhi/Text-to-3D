@echo off
setlocal

cd /d "%~dp0"

if not exist "backend\venv\Scripts\python.exe" (
    py -m venv backend\venv
)

call "backend\venv\Scripts\activate.bat"
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt

pushd frontend
if not exist "node_modules" (
    npm install
)
npm run build
popd

start "Text-to-3D Backend" cmd /k ""%~dp0backend-start.bat""

timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:8000"
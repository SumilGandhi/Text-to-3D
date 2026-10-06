@echo off
setlocal

cd /d "%~dp0backend"
call "%~dp0backend\venv\Scripts\activate.bat"
python -m uvicorn main:app --host 127.0.0.1 --port 8000
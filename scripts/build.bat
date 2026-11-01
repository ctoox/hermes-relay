@echo off
chcp 65001 >nul
title Hermes Relay - Build

echo.
echo ============================================================
echo   Hermes Relay - Build EXE
echo ============================================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found
    pause
    exit /b 1
)

echo [1/4] Setting up environment...
if not exist ".venv" (
    python -m venv .venv
)
call .venv\Scripts\activate.bat

echo [2/4] Installing dependencies...
pip install -r requirements.txt --quiet
pip install PySide6 --quiet
pip install pyinstaller --quiet

echo [3/4] Building with PyInstaller...
echo.

pyinstaller --noconfirm --clean ^
    --onefile ^
    --windowed ^
    --icon=app.ico ^
    --name=HermesRelay ^
    --add-data="config;config" ^
    --add-data="relay_server;relay_server" ^
    --add-data="agent_client;agent_client" ^
    --add-data="shared;shared" ^
    --hidden-import=websockets ^
    --hidden-import=yaml ^
    --hidden-import=psutil ^
    --hidden-import=lark_oapi ^
    --hidden-import=qrcode ^
    --hidden-import=PIL ^
    --hidden-import=mss ^
    --hidden-import=pyautogui ^
    desktop_app.py

echo.
echo [4/4] Copying resources...

if not exist "dist\config" mkdir dist\config
copy config\*.yaml dist\config\ >nul 2>&1
copy config\*.example.yaml dist\config\ >nul 2>&1

echo.
echo ============================================================
echo   Build Complete!
echo ============================================================
echo.
echo   Output: dist\HermesRelay.exe
echo.
echo   Files:
dir /b dist\
echo.

pause

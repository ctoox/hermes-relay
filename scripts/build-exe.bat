@echo off
chcp 65001 >nul
title Hermes Relay - Build EXE

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

echo [1/4] Creating virtual environment...
if not exist ".venv" (
    python -m venv .venv
)
call .venv\Scripts\activate.bat

echo [2/4] Installing dependencies...
pip install -r requirements.txt --quiet
pip install PySide6 --quiet
pip install nuitka --quiet
pip install ordered-set --quiet

echo [3/4] Building with Nuitka...
echo.

python -m nuitka ^
    --standalone ^
    --onefile ^
    --windows-console-mode=disable ^
    --windows-icon-from-ico=app.ico ^
    --enable-plugin=pyside6 ^
    --company-name=Hermes ^
    --product-name="Hermes Relay" ^
    --file-version=1.0.0 ^
    --product-version=1.0.0 ^
    --file-description="Hermes Relay Remote Control" ^
    --output-dir=dist ^
    --output-filename=HermesRelay.exe ^
    desktop_app.py

echo.
echo [4/4] Copying resources...

if not exist "dist\config" mkdir dist\config
copy config\*.yaml dist\config\ >nul 2>&1
copy config\*.example.yaml dist\config\ >nul 2>&1
copy app.ico dist\ >nul 2>&1

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

@echo off
chcp 65001 >nul
title Hermes Relay - 启动服务端

echo.
echo ============================================================
echo   Hermes Relay - 中转站服务端
echo ============================================================
echo.

REM 检查配置
if not exist "config\relay_config.yaml" (
    echo ⚠️  未找到配置文件，将使用默认配置
    echo    如需配置，请运行: scripts\setup.bat
    echo.
)

REM 检查依赖
pip install -r requirements.txt --quiet 2>nul

echo 📡 启动中转站服务端...
echo.

python hermes_relay.py server --config config\relay_config.yaml

pause

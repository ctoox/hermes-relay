@echo off
chcp 65001 >nul
title Hermes Relay - 一键启动

echo.
echo ============================================================
echo   Hermes Relay - 一键启动
echo ============================================================
echo.

REM 检查配置
if not exist "config\relay_config.yaml" (
    echo ❌ 未找到配置文件，请先运行: scripts\setup.bat
    pause
    exit /b 1
)

REM 检查依赖
pip install -r requirements.txt --quiet 2>nul

echo 🚀 启动中...
echo.

python hermes_relay.py start

pause

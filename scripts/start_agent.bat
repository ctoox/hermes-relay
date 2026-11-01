@echo off
chcp 65001 >nul
title Hermes Relay - 启动被控端

echo.
echo ============================================================
echo   Hermes Relay - 被控端 Agent
echo ============================================================
echo.

REM 检查配置
if not exist "config\agent_config.yaml" (
    echo ⚠️  未找到配置文件，将使用默认配置
    echo    如需配置，请运行: scripts\setup.bat
    echo.
)

REM 检查依赖
pip install -r requirements.txt --quiet 2>nul

echo 💻 启动被控端 Agent...
echo.

python hermes_relay.py agent --config config\agent_config.yaml

pause

@echo off
chcp 65001 >nul
title Hermes Relay - 一键设置

echo.
echo ============================================================
echo   Hermes Relay - 远程控制系统
echo ============================================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到 Python，请安装 Python 3.8+
    echo    下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM 检查依赖
echo 📦 检查依赖...
pip install -r requirements.txt --quiet 2>nul

echo.
echo 请选择操作:
echo.
echo   1. 快速设置 (扫码配置 + 一键启动)
echo   2. 完整设置向导
echo   3. 扫码配置飞书机器人
echo   4. 启动服务端
echo   5. 启动被控端
echo   6. 一键启动 (服务端 + 被控端)
echo   0. 退出
echo.

set /p choice="请选择 [0-6]: "

if "%choice%"=="1" goto quick_setup
if "%choice%"=="2" goto full_setup
if "%choice%"=="3" goto onboard
if "%choice%"=="4" goto start_server
if "%choice%"=="5" goto start_agent
if "%choice%"=="6" goto start_all
if "%choice%"=="0" goto end

echo 无效选择
pause
goto end

:quick_setup
echo.
echo 🚀 快速设置...
python hermes_relay.py quick
pause
goto end

:full_setup
echo.
echo 🔧 完整设置向导...
python hermes_relay.py setup
pause
goto end

:onboard
echo.
echo 📱 扫码配置飞书机器人...
python hermes_relay.py onboard
pause
goto end

:start_server
echo.
echo 📡 启动中转站服务端...
python hermes_relay.py server
pause
goto end

:start_agent
echo.
echo 💻 启动被控端 Agent...
python hermes_relay.py agent
pause
goto end

:start_all
echo.
echo 🚀 一键启动...
python hermes_relay.py start
pause
goto end

:end

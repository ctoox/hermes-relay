@echo off
chcp 65001 >nul
title Hermes Relay - 一键打包

echo.
echo ============================================================
echo   Hermes Relay - 一键打包
echo ============================================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到 Python，请安装 Python 3.8+
    pause
    exit /b 1
)

echo 📦 步骤 1/3: 安装依赖...
pip install pyinstaller --quiet 2>nul
pip install -r requirements.txt --quiet 2>nul

echo 🔨 步骤 2/3: 打包中...
echo.

REM 创建输出目录
if not exist "dist" mkdir dist
if not exist "dist\hermes-relay" mkdir dist\hermes-relay

REM 打包服务端
echo   [1/3] 打包服务端...
pyinstaller --onefile --name hermes-relay-server --distpath dist\hermes-relay hermes_relay.py --noconfirm --clean 2>nul

REM 打包 Agent
echo   [2/3] 打包 Agent...
pyinstaller --onefile --name hermes-relay-agent --distpath dist\hermes-relay hermes_relay.py --noconfirm --clean 2>nul

REM 打包设置工具
echo   [3/3] 打包设置工具...
pyinstaller --onefile --name hermes-relay-setup --distpath dist\hermes-relay hermes_relay.py --noconfirm --clean 2>nul

echo.
echo 📁 步骤 3/3: 复制配置文件...

REM 复制配置文件
if not exist "dist\hermes-relay\config" mkdir dist\hermes-relay\config
copy config\*.yaml dist\hermes-relay\config\ >nul 2>&1
copy config\*.example.yaml dist\hermes-relay\config\ >nul 2>&1

REM 复制脚本
copy scripts\*.bat dist\hermes-relay\ >nul 2>&1

REM 创建启动脚本
echo @echo off > dist\hermes-relay\启动服务端.bat
echo chcp 65001 ^>nul >> dist\hermes-relay\启动服务端.bat
echo title Hermes Relay 服务端 >> dist\hermes-relay\启动服务端.bat
echo hermes-relay-server.exe server --config config\relay_config.yaml >> dist\hermes-relay\启动服务端.bat
echo pause >> dist\hermes-relay\启动服务端.bat

echo @echo off > dist\hermes-relay\启动Agent.bat
echo chcp 65001 ^>nul >> dist\hermes-relay\启动Agent.bat
echo title Hermes Relay Agent >> dist\hermes-relay\启动Agent.bat
echo hermes-relay-agent.exe agent --config config\agent_config.yaml >> dist\hermes-relay\启动Agent.bat
echo pause >> dist\hermes-relay\启动Agent.bat

echo @echo off > dist\hermes-relay\初始设置.bat
echo chcp 65001 ^>nul >> dist\hermes-relay\初始设置.bat
echo title Hermes Relay 设置 >> dist\hermes-relay\初始设置.bat
echo hermes-relay-setup.exe setup >> dist\hermes-relay\初始设置.bat
echo pause >> dist\hermes-relay\初始设置.bat

echo.
echo ✅ 打包完成!
echo.
echo 📁 输出目录: dist\hermes-relay\
echo.
echo 文件列表:
dir /b dist\hermes-relay\
echo.
echo 📋 使用方法:
echo   1. 将 dist\hermes-relay\ 整个目录复制到目标机器
echo   2. 运行 "初始设置.bat" 进行配置
echo   3. 运行 "启动服务端.bat" 或 "启动Agent.bat"
echo.

REM 创建压缩包
echo 📦 创建压缩包...
powershell -Command "Compress-Archive -Path 'dist\hermes-relay\*' -DestinationPath 'dist\hermes-relay.zip' -Force"
echo ✅ 压缩包已创建: dist\hermes-relay.zip
echo.

pause

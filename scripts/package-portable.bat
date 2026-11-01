@echo off
chcp 65001 >nul
title Hermes Relay - 便携版打包

echo.
echo ============================================================
echo   Hermes Relay - 便携版打包
echo ============================================================
echo.

REM 创建输出目录
set OUTPUT_DIR=dist\hermes-relay-portable
if not exist "dist" mkdir dist
if exist "%OUTPUT_DIR%" rmdir /s /q "%OUTPUT_DIR%"
mkdir "%OUTPUT_DIR%"

echo 📁 复制文件...

REM 复制源代码
xcopy /E /I /Q relay_server "%OUTPUT_DIR%\relay_server" >nul
xcopy /E /I /Q agent_client "%OUTPUT_DIR%\agent_client" >nul
xcopy /E /I /Q shared "%OUTPUT_DIR%\shared" >nul
if not exist "%OUTPUT_DIR%\config" mkdir "%OUTPUT_DIR%\config"

REM 复制配置文件
copy config\*.example.yaml "%OUTPUT_DIR%\config\" >nul 2>&1

REM 复制主程序
copy hermes_relay.py "%OUTPUT_DIR%\" >nul
copy requirements.txt "%OUTPUT_DIR%\" >nul

REM 复制文档
copy README.md "%OUTPUT_DIR%\" >nul 2>&1

echo 📝 创建启动脚本...

REM 创建安装脚本
(
echo @echo off
echo chcp 65001 ^>nul
echo title Hermes Relay - 安装依赖
echo.
echo echo 正在安装依赖...
echo pip install -r requirements.txt --quiet
echo.
echo echo ✅ 依赖安装完成!
echo echo.
echo echo 请运行以下命令:
echo echo   初始设置.bat  - 首次配置
echo echo   启动服务端.bat - 启动中转站
echo echo   启动Agent.bat  - 启动被控端
echo echo.
echo pause
) > "%OUTPUT_DIR%\安装依赖.bat"

REM 创建初始设置脚本
(
echo @echo off
echo chcp 65001 ^>nul
echo title Hermes Relay - 初始设置
echo.
echo python hermes_relay.py setup
echo pause
) > "%OUTPUT_DIR%\初始设置.bat"

REM 创建快速设置脚本
(
echo @echo off
echo chcp 65001 ^>nul
echo title Hermes Relay - 快速设置
echo.
echo python hermes_relay.py quick
echo pause
) > "%OUTPUT_DIR%\快速设置.bat"

REM 创建启动服务端脚本
(
echo @echo off
echo chcp 65001 ^>nul
echo title Hermes Relay - 服务端
echo.
echo if not exist "config\relay_config.yaml" ^(
echo     echo 未找到配置文件，请先运行 初始设置.bat
echo     pause
echo     exit /b 1
echo ^)
echo.
echo python hermes_relay.py server --config config\relay_config.yaml
echo pause
) > "%OUTPUT_DIR%\启动服务端.bat"

REM 创建启动 Agent 脚本
(
echo @echo off
echo chcp 65001 ^>nul
echo title Hermes Relay - Agent
echo.
echo if not exist "config\agent_config.yaml" ^(
echo     echo 未找到配置文件，请先运行 初始设置.bat
echo     pause
echo     exit /b 1
echo ^)
echo.
echo python hermes_relay.py agent --config config\agent_config.yaml
echo pause
) > "%OUTPUT_DIR%\启动Agent.bat"

REM 创建一键启动脚本
(
echo @echo off
echo chcp 65001 ^>nul
echo title Hermes Relay - 一键启动
echo.
echo python hermes_relay.py start
echo pause
) > "%OUTPUT_DIR%\一键启动.bat"

REM 创建使用说明
(
echo Hermes Relay - 便携版
echo =====================
echo.
echo 首次使用:
echo 1. 双击 "安装依赖.bat" 安装 Python 依赖
echo 2. 双击 "快速设置.bat" 扫码配置飞书机器人
echo 3. 双击 "启动服务端.bat" 启动中转站
echo 4. 在其他电脑双击 "启动Agent.bat" 连接到中转站
echo.
echo 前置条件:
echo - Python 3.8+ (https://www.python.org/downloads/)
echo.
echo 功能:
echo - 飞书扫码配置
echo - 自然语言控制电脑
echo - 截图发送
echo - 鼠标点击控制
echo - 文件传输
echo - 多设备群控
echo.
echo 配置文件位置: config\
echo 日志文件位置: *.log
) > "%OUTPUT_DIR%\使用说明.txt"

echo.
echo ✅ 便携版打包完成!
echo.
echo 📁 输出目录: %OUTPUT_DIR%\
echo.
echo 文件列表:
dir /b "%OUTPUT_DIR%"
echo.
echo 📋 使用方法:
echo   1. 将 %OUTPUT_DIR%\ 整个目录复制到目标机器
echo   2. 确保目标机器已安装 Python 3.8+
echo   3. 双击 "安装依赖.bat"
echo   4. 双击 "快速设置.bat" 或 "初始设置.bat"
echo.

REM 创建压缩包
echo 📦 创建压缩包...
powershell -Command "Compress-Archive -Path '%OUTPUT_DIR%\*' -DestinationPath 'dist\hermes-relay-portable.zip' -Force"
echo ✅ 压缩包已创建: dist\hermes-relay-portable.zip
echo.

pause

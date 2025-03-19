@echo off
REM AI命令执行系统启动脚本 - Windows版本

echo ===============================================
echo   AI远程命令执行系统启动
echo ===============================================

REM 获取脚本所在目录
set SCRIPT_DIR=%~dp0
cd /d %SCRIPT_DIR%

REM 检查环境变量配置
if not exist "%SCRIPT_DIR%ai_mqtt_langchain\.env" (
    echo 错误: 未找到.env文件
    echo 正在从示例文件创建...
    copy "%SCRIPT_DIR%ai_mqtt_langchain\.env.example" "%SCRIPT_DIR%ai_mqtt_langchain\.env" >nul
    echo 请编辑 %SCRIPT_DIR%ai_mqtt_langchain\.env 文件，设置您的API密钥和配置参数
    pause
    exit /b 1
)

REM 加载环境变量
for /f "tokens=1,2 delims==" %%a in (%SCRIPT_DIR%ai_mqtt_langchain\.env) do (
    if not "%%a"=="" if not "%%a:~0,1%"=="#" (
        set "%%a=%%b"
    )
)

REM 检查API密钥是否存在
if "%OPENAI_API_KEY%"=="" (
    echo 错误: OPENAI_API_KEY未设置，请在.env文件中配置
    pause
    exit /b 1
)

REM 确认系统依赖安装
echo 检查系统依赖...
python -c "import paho.mqtt.client" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo 错误: 缺少paho-mqtt库，请运行 pip install -r requirements.txt
    pause
    exit /b 1
)

python -c "import langchain" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo 错误: 缺少langchain库，请运行 pip install -r requirements.txt
    pause
    exit /b 1
)

REM 检查MQTT服务器
echo 检查MQTT服务器...
sc query mosquitto | findstr "RUNNING" >nul
if %ERRORLEVEL% NEQ 0 (
    echo MQTT服务器未运行，尝试启动...
    net start mosquitto
    if %ERRORLEVEL% NEQ 0 (
        echo 无法启动MQTT服务器，请检查Mosquitto是否已安装
        echo 可能需要以管理员身份运行此脚本
        pause
        exit /b 1
    )
)

echo MQTT服务器运行中...

REM 获取设备列表
set DEVICE_LIST=%DEVICE_IDS%
if "%DEVICE_LIST%"=="" (
    echo 警告: 未找到设备配置，使用默认设备ID: rpi_001
    set DEVICE_LIST=rpi_001
)

REM 将设备列表分割为数组
set i=0
for %%a in (%DEVICE_LIST:,= %) do (
    set /a i+=1
    set "DEVICE[!i!]=%%a"
    set "LAST_INDEX=!i!"
)

REM 显示设备列表
echo 可用设备:
for /l %%i in (1,1,%LAST_INDEX%) do (
    echo   %%i. !DEVICE[%%i]!
)

REM 选择设备
if %LAST_INDEX% GTR 1 (
    set /p selection=请选择要连接的设备 (1-%LAST_INDEX%): 
    
    REM 验证输入
    set "valid=0"
    for /l %%i in (1,1,%LAST_INDEX%) do (
        if "!selection!"=="%%i" set "valid=1"
    )
    
    if "!valid!"=="0" (
        echo 无效选择，使用第一个设备
        set "selection=1"
    )
    
    set "DEVICE=!DEVICE[%selection%]!"
) else (
    set "DEVICE=!DEVICE[1]!"
)

echo 使用设备: %DEVICE%

REM 启动AI命令代理
echo 启动AI命令代理...
start "" python "%SCRIPT_DIR%ai_mqtt_langchain\langchain_command_agent.py" --device-id "%DEVICE%"

echo 服务已启动
echo 请勿关闭此窗口，关闭窗口将终止服务
echo 按任意键停止服务...

pause >nul
taskkill /f /fi "WINDOWTITLE eq langchain_command_agent.py*" >nul 2>nul
echo 系统已停止
pause 
@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo 启动树莓派AI命令控制中心Web界面...

REM 检查Python是否安装
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo 错误: 未找到Python，请确保已安装Python并添加到PATH环境变量
    exit /b 1
)

REM 设置PYTHONIOENCODING环境变量确保正确处理UTF-8
set PYTHONIOENCODING=utf-8

REM 检查是否已安装所需依赖
python -c "import flask" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo 安装所需依赖...
    pip install -r requirements.txt
    if %ERRORLEVEL% neq 0 (
        echo 错误: 安装依赖失败
        exit /b 1
    )
)

REM 检查OpenAI API密钥
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('OPENAI_API_KEY'))" > temp.txt
set /p API_KEY=<temp.txt
del temp.txt
if "!API_KEY!"=="" (
    echo 警告: 未设置OpenAI API密钥，请在.env文件中配置或设置环境变量
)

REM 启动Web服务器
echo 启动Web服务器...
python start_web.py %*

if %ERRORLEVEL% neq 0 (
    echo 错误: 启动Web服务器失败
    exit /b 1
)

exit /b 0 
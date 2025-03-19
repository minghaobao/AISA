#!/bin/bash
# AI命令执行系统启动脚本

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# 显示欢迎信息
echo "==============================================="
echo "  AI远程命令执行系统启动"
echo "==============================================="

# 检查环境变量配置
if [ ! -f "$SCRIPT_DIR/ai_mqtt_langchain/.env" ]; then
    echo "错误: 未找到.env文件"
    echo "正在从示例文件创建..."
    cp "$SCRIPT_DIR/ai_mqtt_langchain/.env.example" "$SCRIPT_DIR/ai_mqtt_langchain/.env"
    echo "请编辑 $SCRIPT_DIR/ai_mqtt_langchain/.env 文件，设置您的API密钥和配置参数"
    exit 1
fi

# 加载环境变量
source "$SCRIPT_DIR/ai_mqtt_langchain/.env"
if [ -z "$OPENAI_API_KEY" ]; then
    echo "错误: OPENAI_API_KEY未设置，请在.env文件中配置"
    exit 1
fi

# 确认系统依赖安装
echo "检查系统依赖..."
python -c "import paho.mqtt.client" 2>/dev/null || { echo "错误: 缺少paho-mqtt库，请运行 pip install -r requirements.txt"; exit 1; }
python -c "import langchain" 2>/dev/null || { echo "错误: 缺少langchain库，请运行 pip install -r requirements.txt"; exit 1; }

# 检查MQTT服务器
echo "检查MQTT服务器..."
OS=$(uname -s)
if [ "$OS" = "Linux" ]; then
    # Linux系统
    systemctl is-active --quiet mosquitto
    if [ $? -ne 0 ]; then
        echo "MQTT服务器未运行，尝试启动..."
        sudo systemctl start mosquitto || { echo "无法启动MQTT服务器，请检查安装"; exit 1; }
    fi
elif [ "$OS" = "Darwin" ]; then
    # macOS系统
    brew services list | grep mosquitto | grep started > /dev/null
    if [ $? -ne 0 ]; then
        echo "MQTT服务器未运行，尝试启动..."
        brew services start mosquitto || { echo "无法启动MQTT服务器，请检查安装"; exit 1; }
    fi
else
    # 其他系统（包括Windows），只提示检查
    echo "请确保MQTT服务器已运行。在Windows上，使用服务管理器检查Mosquitto服务。"
    read -p "MQTT服务器是否已运行? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        echo "请先启动MQTT服务器"
        exit 1
    fi
fi

echo "MQTT服务器运行中..."

# 定义清理函数
cleanup() {
    echo "接收到终止信号，正在停止服务..."
    kill $AGENT_PID 2>/dev/null
    echo "系统已停止"
    exit 0
}

# 设置信号处理
trap cleanup SIGINT SIGTERM

# 获取可用设备列表
IFS=',' read -r -a DEVICES <<< "$DEVICE_IDS"
if [ ${#DEVICES[@]} -eq 0 ]; then
    echo "警告: 未找到设备配置，使用默认设备ID: rpi_001"
    DEVICES=("rpi_001")
fi

# 显示设备列表
echo "可用设备:"
for i in "${!DEVICES[@]}"; do
    echo "  $((i+1)). ${DEVICES[$i]}"
done

# 选择设备
if [ ${#DEVICES[@]} -gt 1 ]; then
    echo "请选择要连接的设备 (1-${#DEVICES[@]}):"
    read -r selection
    if ! [[ "$selection" =~ ^[0-9]+$ ]] || [ "$selection" -lt 1 ] || [ "$selection" -gt ${#DEVICES[@]} ]; then
        echo "无效选择，使用第一个设备"
        DEVICE=${DEVICES[0]}
    else
        DEVICE=${DEVICES[$((selection-1))]}
    fi
else
    DEVICE=${DEVICES[0]}
fi

echo "使用设备: $DEVICE"

# 启动AI命令代理
echo "启动AI命令代理..."
python "$SCRIPT_DIR/ai_mqtt_langchain/langchain_command_agent.py" --device-id "$DEVICE" &
AGENT_PID=$!

echo "服务启动完成，PID: $AGENT_PID"
echo "按 Ctrl+C 停止服务"

# 等待进程完成
wait $AGENT_PID 
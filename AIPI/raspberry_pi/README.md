# 树莓派 AI MQTT LangChain 服务

本目录包含需要在树莓派端运行的服务组件，用于设备控制、数据采集和处理。

## 目录结构

- `device_controller.py` - 设备控制模块，用于操作GPIO引脚和控制外接设备
- `mqtt_client.py` - MQTT客户端，用于与MQTT服务器通信
- `langchain_processor.py` - LangChain处理器，用于分析设备数据并提供智能控制
- `langchain_command_agent.py` - 命令代理，处理自然语言命令
- `rpi_run.py` - 树莓派服务启动脚本

## 安装步骤

1. 在树莓派上安装所需软件包：

```bash
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv
```

2. 创建并激活虚拟环境：

```bash
python3 -m venv env
source env/bin/activate
```

3. 安装依赖包：

```bash
pip install paho-mqtt langchain openai python-dotenv RPi.GPIO
```

4. 配置环境变量：

在项目根目录创建`.env`文件，填入以下内容：

```
# MQTT配置
MQTT_HOST=your_mqtt_server
MQTT_PORT=1883
MQTT_USERNAME=your_username
MQTT_PASSWORD=your_password

# OpenAI API配置
OPENAI_API_KEY=your_openai_api_key

# 设备ID
DEVICE_ID=rpi_001

# 日志配置
LOG_LEVEL=INFO
```

## 启动服务

启动所有服务：

```bash
python rpi_run.py --all
```

或者单独启动各个组件：

```bash
# 只启动MQTT客户端
python rpi_run.py --mqtt

# 只初始化设备控制器
python rpi_run.py --device

# 只启动LangChain处理器
python rpi_run.py --processor
```

## 设备配置

设备配置位于项目根目录的`config.py`文件中的`DEVICE_CONFIG`部分。您可以根据实际连接的硬件设备进行修改。

## 故障排除

1. GPIO访问权限问题：

```bash
sudo usermod -a -G gpio <your_username>
```

2. 检查MQTT连接：

```bash
mosquitto_sub -h <mqtt_host> -p <mqtt_port> -t "device/+/data" -u <username> -P <password>
```

3. 查看日志：

```bash
tail -f rpi_service.log
``` 
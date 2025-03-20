# 树莓派端安装指南

本指南详细说明如何在树莓派设备上安装和配置AIPI客户端。

## 1. 环境要求

- 树莓派 3B+ 或更高版本（推荐树莓派 4B）
- 树莓派 OS (Bullseye 或更新版本)
- Python 3.8+
- 适当的GPIO连接设备（继电器、传感器等）
- 网络连接（有线网络或WiFi）

## 2. 硬件准备

根据你的具体需求，你可能需要以下硬件：

- 继电器模块（控制高功率设备）
- 风扇（需要PWM控制的推荐使用适配器）
- LED灯或其他照明设备
- DHT11/DHT22温湿度传感器
- 其他GPIO兼容的传感器和执行器

### 2.1 GPIO连接示例

以下是一些常见设备的GPIO连接示例：

**继电器连接**
- GPIO17 -> 继电器1输入
- GPIO18 -> 继电器2输入
- 5V -> 继电器VCC
- GND -> 继电器GND

**DHT22温湿度传感器**
- GPIO4 -> DHT22数据引脚
- 3.3V -> DHT22 VCC
- GND -> DHT22 GND

**LED灯**
- GPIO24 -> LED阳极（通过220-330Ω电阻）
- GND -> LED阴极

## 3. 软件安装

### 3.1 系统准备

确保你的树莓派系统已更新：

```bash
sudo apt update
sudo apt upgrade -y
```

安装必要的系统依赖：

```bash
sudo apt install -y python3-pip python3-dev python3-setuptools git
sudo apt install -y libgpiod2  # GPIO支持
```

### 3.2 获取代码

克隆AIPI代码库：

```bash
git clone https://github.com/yourusername/AIPI.git
cd AIPI/raspberry_pi
```

### 3.3 安装Python依赖

创建并激活虚拟环境（推荐）：

```bash
python3 -m venv venv
source venv/bin/activate  # 在Windows上使用 venv\Scripts\activate
```

安装项目依赖：

```bash
pip install -r requirements.txt
```

## 4. 配置

### 4.1 基本配置

复制示例配置文件：

```bash
cp .env.example .env
```

编辑`.env`文件，设置以下必要参数：

```
# 设备标识符（必需-唯一标识设备）
DEVICE_ID=raspberry_pi_001

# MQTT连接配置（必需-用于数据传输和命令接收）
MQTT_HOST=your_mqtt_server_address
MQTT_PORT=1883
MQTT_USERNAME=your_username
MQTT_PASSWORD=your_password

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=raspberry_pi.log

# 数据收集配置
DATA_COLLECTION_INTERVAL=60
COLLECT_CPU=True
COLLECT_MEMORY=True
COLLECT_DISK=True
COLLECT_NETWORK=True
COLLECT_TEMPERATURE=True
```

如果需要使用LangChain功能，还需要设置OpenAI API密钥：

```
# OpenAI API配置（用于LangChain处理器）
OPENAI_API_KEY=your_openai_api_key
LLM_MODEL=gpt-3.5-turbo
LLM_TEMPERATURE=0.1
```

### 4.2 硬件配置

创建`.env.local`文件来配置特定于设备的硬件设置：

```bash
cp .env.example .env.local
```

编辑`.env.local`文件，根据你的硬件连接设置GPIO引脚：

```
# 设备标识符（覆盖.env中的默认值）
DEVICE_ID=raspberry_pi_kitchen_001

# GPIO引脚配置
RELAY_1_PIN=17
RELAY_2_PIN=18
FAN_1_PIN=22
FAN_1_PWM_PIN=23
LIGHT_1_PIN=24

# 传感器引脚
DHT_SENSOR_PIN=4
```

## 5. 运行

### 5.1 启动所有服务

要启动所有服务（MQTT客户端、设备控制器和LangChain处理器）：

```bash
python rpi_run.py
```

### 5.2 启动特定服务

如果你只想启动特定的服务：

```bash
# 只启动MQTT客户端
python rpi_run.py --mqtt

# 只启动设备控制器
python rpi_run.py --device

# 只启动LangChain处理器
python rpi_run.py --processor
```

### 5.3 设置开机自启

为了让树莓派在启动时自动运行AIPI客户端，你可以创建一个systemd服务：

创建服务文件：

```bash
sudo nano /etc/systemd/system/aipi.service
```

添加以下内容（需要根据你的安装路径和配置调整）：

```
[Unit]
Description=AIPI Raspberry Pi Client
After=network.target mosquitto.service

[Service]
User=pi
WorkingDirectory=/home/pi/AIPI/raspberry_pi
ExecStart=/home/pi/AIPI/raspberry_pi/venv/bin/python rpi_run.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

启用并启动服务：

```bash
sudo systemctl enable aipi.service
sudo systemctl start aipi.service
```

查看服务状态：

```bash
sudo systemctl status aipi.service
```

## 6. 测试

### 6.1 测试设备控制

你可以通过MQTT消息测试设备控制。使用任何MQTT客户端（如MQTT Explorer或mosquitto_pub）发送命令：

```bash
# 打开继电器1
mosquitto_pub -h your_mqtt_server -t "device/control" -m '{"device_id":"relay_1","action":"on"}'

# 关闭继电器1
mosquitto_pub -h your_mqtt_server -t "device/control" -m '{"device_id":"relay_1","action":"off"}'

# 设置风扇速度
mosquitto_pub -h your_mqtt_server -t "device/control" -m '{"device_id":"fan_1","action":"speed","parameters":{"speed":50}}'
```

### 6.2 测试数据收集

设备数据将自动按配置的间隔发布到MQTT主题。你可以订阅数据主题查看发布的数据：

```bash
mosquitto_sub -h your_mqtt_server -t "device/raspberry_pi_001/data" -v
```

### 6.3 测试自然语言命令

如果配置了LangChain处理器，你可以通过以下主题发送自然语言命令：

```bash
mosquitto_pub -h your_mqtt_server -t "langchain/process/raspberry_pi_001" -m '{"query":"打开客厅的灯","device_id":"raspberry_pi_001"}'
```

## 7. 故障排除

### 7.1 MQTT连接问题

如果无法连接到MQTT服务器：
- 确认MQTT服务器地址和端口正确
- 验证用户名和密码
- 检查网络连接和防火墙设置
- 查看日志文件中的详细错误信息

### 7.2 GPIO权限问题

如果遇到GPIO权限问题：
- 确保你的用户在gpio组中：`sudo usermod -a -G gpio $USER`
- 重新登录或重启树莓派应用权限更改
- 使用sudo运行脚本（不推荐长期使用）

### 7.3 温度传感器故障

如果无法读取温度：
- 检查传感器连接
- 确认已安装所需库：`pip install adafruit-circuitpython-dht`
- 可能需要安装系统依赖：`sudo apt install libgpiod2`

## 8. 高级配置

### 8.1 使用外部传感器

AIPI支持多种传感器。要添加自定义传感器，你需要：

1. 在`.env.local`文件中添加传感器引脚配置
2. 修改`device_controller.py`添加传感器读取逻辑
3. 调整数据收集代码收集新传感器数据

### 8.2 优化性能

对于资源受限的树莓派（如Pi Zero或3B），你可以：

- 增加数据收集间隔减少CPU使用率
- 禁用不必要的数据收集（如磁盘、网络）
- 减小日志级别`LOG_LEVEL=WARNING`
- 禁用LangChain处理器（运行`python rpi_run.py --mqtt --device`）

## 9. 扩展阅读

- [树莓派GPIO编程](https://www.raspberrypi.org/documentation/usage/gpio/)
- [MQTT协议简介](https://mqtt.org/getting-started/)
- [LangChain文档](https://python.langchain.com/en/latest/)
- [设备控制器开发指南](extending_devices.md) 
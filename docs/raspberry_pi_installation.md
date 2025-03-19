# 树莓派安装指南

本文档提供了在树莓派上安装和配置AI命令执行系统的详细说明。

## 系统要求

- 树莓派 3B+ 或更高版本
- Raspberry Pi OS (原Raspbian) Buster或更新版本
- 至少2GB的可用存储空间
- 网络连接（有线或无线）

## 基础系统设置

### 1. 更新系统

首先，确保您的树莓派系统是最新的：

```bash
sudo apt update
sudo apt upgrade -y
```

### 2. 安装必要的依赖

```bash
# 安装Python3和pip（大多数树莓派OS已预装）
sudo apt install -y python3 python3-pip

# 安装系统依赖
sudo apt install -y git mosquitto mosquitto-clients

# 设置并启动MQTT服务器
sudo systemctl enable mosquitto
sudo systemctl start mosquitto
```

## 安装AI命令执行系统

### 1. 克隆代码仓库

```bash
git clone https://github.com/yourusername/ai-command-system.git
cd ai-command-system
```

### 2. 安装Python依赖

```bash
pip3 install -r requirements.txt
```

如果您遇到内存问题，可以尝试逐个安装依赖：

```bash
pip3 install paho-mqtt psutil python-dotenv
```

### 3. 配置执行器

创建并编辑配置文件：

```bash
cp ai_mqtt_langchain/rpi_executor_config.json.example ai_mqtt_langchain/rpi_executor_config.json
nano ai_mqtt_langchain/rpi_executor_config.json
```

根据需要修改配置内容：

```json
{
    "device_id": "rpi_001",  # 为您的设备设置一个唯一ID
    "mqtt_host": "localhost",  # 如果MQTT服务器在另一台机器上，更改此值
    "mqtt_port": 1883,
    "mqtt_username": "mqtt_user",  # 如果配置了MQTT认证
    "mqtt_password": "mqtt_password",  # 如果配置了MQTT认证
    "heartbeat_interval": 30
}
```

## 设置自启动服务

为了确保命令执行器在树莓派启动时自动运行，我们可以创建一个系统服务：

### 1. 创建服务文件

```bash
sudo nano /etc/systemd/system/rpi-command-executor.service
```

### 2. 添加以下内容

```
[Unit]
Description=Raspberry Pi Command Executor
After=network.target mosquitto.service

[Service]
ExecStart=/usr/bin/python3 /home/pi/ai-command-system/ai_mqtt_langchain/rpi_command_executor.py
WorkingDirectory=/home/pi/ai-command-system
StandardOutput=inherit
StandardError=inherit
Restart=always
User=pi

[Install]
WantedBy=multi-user.target
```

注意：请根据您的安装路径调整上述文件中的路径。

### 3. 启用并启动服务

```bash
sudo systemctl daemon-reload
sudo systemctl enable rpi-command-executor.service
sudo systemctl start rpi-command-executor.service
```

### 4. 检查服务状态

```bash
sudo systemctl status rpi-command-executor.service
```

## 测试系统

安装完成后，您可以通过以下方式测试系统是否正常工作：

### 1. 检查日志

```bash
sudo journalctl -u rpi-command-executor.service -f
```

### 2. 发送测试命令

在服务器端运行：

```bash
python3 ai_mqtt_langchain/send_rpi_command.py --device-id rpi_001 --command "echo 测试成功" --mqtt-host <树莓派IP地址>
```

如果一切正常，您应该能在日志中看到命令执行结果。

## 优化树莓派性能

对于长时间运行的应用，可以考虑以下优化：

### 1. 增加交换空间

```bash
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# 修改 CONF_SWAPSIZE=100 为 CONF_SWAPSIZE=1024
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

### 2. 控制CPU温度

```bash
sudo apt install -y python3-gpiozero
```

然后可以使用以下命令监控温度：

```bash
vcgencmd measure_temp
```

## 常见问题解答

### 1. 无法连接到MQTT服务器

检查MQTT服务是否运行：

```bash
sudo systemctl status mosquitto
```

确保防火墙允许1883端口通信：

```bash
sudo ufw allow 1883
```

### 2. 权限问题

如果遇到权限错误，确保执行器服务使用了正确的用户：

```bash
sudo chown -R pi:pi /home/pi/ai-command-system
```

### 3. 设备不响应命令

确保设备ID在服务器和树莓派配置中一致，并检查日志以获取详细错误信息：

```bash
sudo journalctl -u rpi-command-executor.service -n 50
```

## 进阶配置

### 1. 配置MQTT TLS加密

为增强安全性，可以配置MQTT使用TLS加密通信。请参考Mosquitto官方文档。

### 2. 设置GPIO控制权限

如果需要通过命令控制GPIO引脚，确保用户有足够权限：

```bash
sudo usermod -a -G gpio pi
```

### 3. 启用摄像头访问

如果需要执行摄像头相关命令：

```bash
sudo raspi-config
# 在Interface Options中启用Camera
```

## 更新系统

要更新到最新版本：

```bash
cd ai-command-system
git pull
pip3 install -r requirements.txt --upgrade
sudo systemctl restart rpi-command-executor.service
``` 
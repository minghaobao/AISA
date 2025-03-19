# MQTT服务器部署指南

本文档提供了设置MQTT服务器的详细说明，以支持AI命令执行系统的通信需求。

## MQTT简介

MQTT (Message Queuing Telemetry Transport) 是一个轻量级的发布/订阅消息传输协议，设计用于低带宽、高延迟或不可靠的网络环境。它是物联网(IoT)应用的理想选择。

在我们的系统中，MQTT用于以下目的：
- 从服务器向设备发送命令
- 从设备接收命令执行结果
- 接收设备状态更新和心跳信息

## Mosquitto MQTT服务器

Mosquitto是一个开源的MQTT消息代理，我们将使用它作为我们的MQTT服务器。以下是在不同平台上安装和配置Mosquitto的指南。

## Linux安装指南

### Ubuntu/Debian系统

1. 安装Mosquitto:
   ```bash
   sudo apt update
   sudo apt install -y mosquitto mosquitto-clients
   ```

2. 允许匿名访问 (用于测试):
   ```bash
   sudo nano /etc/mosquitto/conf.d/default.conf
   ```
   
   添加以下内容:
   ```
   listener 1883
   allow_anonymous true
   ```

3. 重启服务:
   ```bash
   sudo systemctl restart mosquitto
   ```

### 启用安全访问 (推荐用于生产环境)

1. 创建密码文件:
   ```bash
   sudo mosquitto_passwd -c /etc/mosquitto/passwd mqtt_user
   ```
   按提示输入密码。

2. 更新配置:
   ```bash
   sudo nano /etc/mosquitto/conf.d/default.conf
   ```
   
   修改内容:
   ```
   listener 1883
   allow_anonymous false
   password_file /etc/mosquitto/passwd
   ```

3. 重启服务:
   ```bash
   sudo systemctl restart mosquitto
   ```

### 启用TLS加密 (推荐用于公共网络)

1. 创建证书目录:
   ```bash
   sudo mkdir -p /etc/mosquitto/certs
   cd /etc/mosquitto/certs
   ```

2. 生成自签名证书:
   ```bash
   sudo openssl genrsa -out ca.key 2048
   sudo openssl req -new -x509 -days 3650 -key ca.key -out ca.crt
   sudo openssl genrsa -out server.key 2048
   sudo openssl req -new -key server.key -out server.csr
   sudo openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server.crt -days 3650
   ```

3. 更新配置:
   ```bash
   sudo nano /etc/mosquitto/conf.d/default.conf
   ```
   
   添加TLS配置:
   ```
   listener 8883
   cafile /etc/mosquitto/certs/ca.crt
   certfile /etc/mosquitto/certs/server.crt
   keyfile /etc/mosquitto/certs/server.key
   tls_version tlsv1.2
   
   # 使用密码认证
   allow_anonymous false
   password_file /etc/mosquitto/passwd
   ```

4. 重启服务:
   ```bash
   sudo systemctl restart mosquitto
   ```

## Windows安装指南

1. 下载Mosquitto:
   - 访问[Mosquitto官方下载页面](https://mosquitto.org/download/)
   - 下载最新的Windows安装程序

2. 安装Mosquitto:
   - 运行下载的exe文件
   - 按照安装向导完成安装
   - 选择"安装为Windows服务"选项

3. 配置Mosquitto:
   - 打开文件`C:\Program Files\mosquitto\mosquitto.conf`
   - 添加以下配置:
   ```
   listener 1883
   allow_anonymous true
   ```

4. 启动服务:
   - 打开Windows服务管理器
   - 找到"Mosquitto Broker"服务
   - 启动服务并设置为自动启动
   
   或使用命令行:
   ```
   net start mosquitto
   ```

### 启用安全访问 (Windows)

1. 创建密码文件:
   ```
   cd "C:\Program Files\mosquitto"
   mosquitto_passwd -c passwordfile mqtt_user
   ```

2. 更新配置文件:
   ```
   listener 1883
   allow_anonymous false
   password_file passwordfile
   ```

3. 重启服务:
   ```
   net stop mosquitto
   net start mosquitto
   ```

## Docker安装指南

如果您熟悉Docker，这是部署Mosquitto最简单的方式:

1. 创建Docker Compose文件:
   ```bash
   mkdir -p mqtt-server
   cd mqtt-server
   ```

   创建`docker-compose.yml`:
   ```yaml
   version: '3'
   services:
     mosquitto:
       image: eclipse-mosquitto:latest
       container_name: mosquitto
       ports:
         - "1883:1883"
         - "8883:8883"
       volumes:
         - ./config:/mosquitto/config
         - ./data:/mosquitto/data
         - ./log:/mosquitto/log
       restart: unless-stopped
   ```

2. 创建配置目录和文件:
   ```bash
   mkdir -p config data log
   ```

   创建`config/mosquitto.conf`:
   ```
   persistence true
   persistence_location /mosquitto/data/
   log_dest file /mosquitto/log/mosquitto.log
   
   # 普通TCP监听器
   listener 1883
   
   # 可选: 启用密码认证
   # allow_anonymous false
   # password_file /mosquitto/config/passwd
   
   # 默认允许匿名访问(测试用)
   allow_anonymous true
   ```

3. 启动服务:
   ```bash
   docker-compose up -d
   ```

4. 添加用户 (可选):
   ```bash
   docker exec -it mosquitto mosquitto_passwd -c /mosquitto/config/passwd mqtt_user
   ```
   
   然后编辑`config/mosquitto.conf`启用密码认证，并重启容器:
   ```bash
   docker-compose restart
   ```

## 测试MQTT服务器

1. 订阅测试主题:
   ```bash
   # Linux/macOS
   mosquitto_sub -h localhost -t "test/topic" -v
   
   # Windows
   "C:\Program Files\mosquitto\mosquitto_sub" -h localhost -t "test/topic" -v
   
   # 如果配置了密码认证
   mosquitto_sub -h localhost -t "test/topic" -v -u mqtt_user -P your_password
   ```

2. 发布测试消息:
   ```bash
   # Linux/macOS
   mosquitto_pub -h localhost -t "test/topic" -m "Hello MQTT!"
   
   # Windows
   "C:\Program Files\mosquitto\mosquitto_pub" -h localhost -t "test/topic" -m "Hello MQTT!"
   
   # 如果配置了密码认证
   mosquitto_pub -h localhost -t "test/topic" -m "Hello MQTT!" -u mqtt_user -P your_password
   ```

## 配置系统使用MQTT服务器

1. 编辑环境变量配置:
   ```bash
   nano ai_mqtt_langchain/.env
   ```
   
   更新以下参数:
   ```
   MQTT_HOST=your_mqtt_server_ip
   MQTT_PORT=1883  # 或 8883 如果使用TLS
   MQTT_USERNAME=mqtt_user  # 如果配置了认证
   MQTT_PASSWORD=your_password  # 如果配置了认证
   ```

2. 更新树莓派设备配置:
   ```bash
   nano ai_mqtt_langchain/rpi_executor_config.json
   ```
   
   更新配置:
   ```json
   {
       "device_id": "rpi_001",
       "mqtt_host": "your_mqtt_server_ip",
       "mqtt_port": 1883,
       "mqtt_username": "mqtt_user",
       "mqtt_password": "your_password",
       "heartbeat_interval": 30
   }
   ```

## 防火墙配置

如果您使用防火墙，确保以下端口是开放的:

- 1883: MQTT默认端口
- 8883: MQTT over TLS端口

### UFW (Ubuntu):
```bash
sudo ufw allow 1883
sudo ufw allow 8883
```

### iptables:
```bash
sudo iptables -A INPUT -p tcp --dport 1883 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 8883 -j ACCEPT
```

### Windows防火墙:
在Windows防火墙高级设置中，创建新的入站规则允许这些端口。

## 性能优化

对于处理大量设备的部署，以下优化可能有用:

1. 增加最大连接数:
   ```
   # 在mosquitto.conf中添加
   max_connections -1  # 无限制
   ```

2. 调整保持连接设置:
   ```
   # 在mosquitto.conf中添加
   persistent_client_expiration 1d  # 未活动客户端的会话过期时间
   ```

## 监控MQTT服务器

为了确保服务器稳定运行，可以设置监控:

1. 检查服务状态:
   ```bash
   sudo systemctl status mosquitto
   ```

2. 查看日志:
   ```bash
   sudo tail -f /var/log/mosquitto/mosquitto.log
   ```

3. 使用第三方监控工具如MQTT Explorer或HiveMQ Web Client。

## 故障排除

### 连接被拒绝

- 检查认证设置:
  ```bash
  sudo cat /etc/mosquitto/passwd
  ```
  
- 确认IP和端口配置正确:
  ```bash
  netstat -tuln | grep 1883
  ```

### TLS证书问题

- 确认证书权限:
  ```bash
  sudo chmod 644 /etc/mosquitto/certs/ca.crt
  sudo chmod 644 /etc/mosquitto/certs/server.crt
  sudo chmod 600 /etc/mosquitto/certs/server.key
  ```

### 服务无法启动

- 检查配置文件语法:
  ```bash
  mosquitto -c /etc/mosquitto/mosquitto.conf -v
  ```

## 资源与参考

- [Mosquitto官方文档](https://mosquitto.org/documentation/)
- [MQTT规范](https://mqtt.org/)
- [Eclipse Mosquitto Docker镜像](https://hub.docker.com/_/eclipse-mosquitto) 
# MQTT服务器设置指南

本指南详细说明如何设置和配置AIPI系统所需的MQTT服务器，用于设备通信和命令传输。

## 1. MQTT简介

MQTT（Message Queuing Telemetry Transport）是一种轻量级的发布/订阅消息传输协议，特别适合物联网设备之间的通信。在AIPI系统中，MQTT服务器（也称为代理或Broker）充当所有设备和服务器端组件之间的中央通信枢纽。

### 1.1 为什么选择MQTT？

- **轻量级**：适合带宽受限的网络环境
- **发布/订阅模式**：解耦消息发送者和接收者
- **可靠的消息传递**：支持不同QoS级别
- **广泛支持**：几乎所有编程语言和平台都有MQTT客户端库
- **适合物联网场景**：设计用于不稳定网络和低功耗设备

## 2. 安装MQTT服务器

AIPI系统推荐使用Mosquitto作为MQTT服务器。这里提供在不同平台上安装Mosquitto的方法。

### 2.1 在Linux上安装（Ubuntu/Debian）

```bash
# 更新包列表
sudo apt update

# 安装Mosquitto服务器和客户端工具
sudo apt install -y mosquitto mosquitto-clients

# 启用并启动Mosquitto服务
sudo systemctl enable mosquitto
sudo systemctl start mosquitto
```

### 2.2 在Windows上安装

1. 从[Mosquitto官方网站](https://mosquitto.org/download/)下载Windows安装程序
2. 运行安装程序，按照向导完成安装
3. 安装完成后，Mosquitto会作为Windows服务自动启动

### 2.3 在macOS上安装

```bash
# 使用Homebrew安装
brew install mosquitto

# 启动服务
brew services start mosquitto
```

### 2.4 使用Docker安装

```bash
# 拉取官方Mosquitto镜像
docker pull eclipse-mosquitto

# 运行Mosquitto容器
docker run -it -p 1883:1883 -p 9001:9001 --name mqtt eclipse-mosquitto
```

## 3. 基本配置

默认情况下，Mosquitto允许无认证访问，这不适合生产环境。我们需要配置认证和访问控制。

### 3.1 创建配置文件

在Linux上，编辑Mosquitto配置文件：

```bash
sudo nano /etc/mosquitto/mosquitto.conf
```

添加或修改以下内容：

```
# 基本设置
listener 1883
allow_anonymous false
password_file /etc/mosquitto/passwd

# 启用持久会话和消息
persistence true
persistence_location /var/lib/mosquitto/

# 日志设置
log_dest file /var/log/mosquitto/mosquitto.log
log_type all
```

### 3.2 创建用户和密码

```bash
# 创建一个名为aisa_server的用户（替换为你选择的用户名）
sudo mosquitto_passwd -c /etc/mosquitto/passwd aisa_server

# 添加其他用户（例如，为树莓派客户端）
sudo mosquitto_passwd -b /etc/mosquitto/passwd aisa_rpi your_secure_password
```

### 3.3 设置权限

为提高安全性，可以设置详细的访问控制列表（ACL）：

```bash
sudo nano /etc/mosquitto/acl.conf
```

添加以下内容：

```
# 服务器端用户可以发布和订阅所有主题
user aisa_server
topic readwrite #

# 树莓派客户端用户只能访问特定主题
user aisa_rpi
topic read device/control
topic write device/+/data
topic write device/+/status
topic read langchain/process/+
topic write langchain/response/+
```

然后在主配置文件中引用ACL文件：

```bash
sudo nano /etc/mosquitto/mosquitto.conf
```

添加：

```
acl_file /etc/mosquitto/acl.conf
```

### 3.4 重启Mosquitto服务

```bash
sudo systemctl restart mosquitto
```

## 4. 启用MQTT Websockets（Web界面支持）

要支持Web浏览器通过WebSockets连接MQTT，需要额外配置：

```bash
sudo nano /etc/mosquitto/mosquitto.conf
```

添加以下内容：

```
# WebSockets支持
listener 9001
protocol websockets
```

重启服务：

```bash
sudo systemctl restart mosquitto
```

## 5. 启用TLS/SSL加密（推荐用于生产环境）

### 5.1 生成自签名证书

```bash
# 创建证书目录
sudo mkdir -p /etc/mosquitto/certs

# 生成CA密钥和证书
sudo openssl genrsa -out /etc/mosquitto/certs/ca.key 2048
sudo openssl req -new -x509 -days 3650 -key /etc/mosquitto/certs/ca.key -out /etc/mosquitto/certs/ca.crt

# 生成服务器密钥和证书签名请求
sudo openssl genrsa -out /etc/mosquitto/certs/server.key 2048
sudo openssl req -new -key /etc/mosquitto/certs/server.key -out /etc/mosquitto/certs/server.csr

# 签名服务器证书
sudo openssl x509 -req -in /etc/mosquitto/certs/server.csr -CA /etc/mosquitto/certs/ca.crt -CAkey /etc/mosquitto/certs/ca.key -CAcreateserial -out /etc/mosquitto/certs/server.crt -days 3650
```

### 5.2 配置TLS/SSL

编辑配置文件启用SSL：

```bash
sudo nano /etc/mosquitto/mosquitto.conf
```

添加以下内容：

```
# 标准MQTT端口（非SSL）
listener 1883 localhost

# SSL/TLS监听端口
listener 8883
cafile /etc/mosquitto/certs/ca.crt
certfile /etc/mosquitto/certs/server.crt
keyfile /etc/mosquitto/certs/server.key
require_certificate false
```

重启服务：

```bash
sudo systemctl restart mosquitto
```

## 6. 测试MQTT服务器

### 6.1 订阅测试主题

在一个终端窗口中订阅主题：

```bash
mosquitto_sub -h localhost -p 1883 -t "test/topic" -u "aisa_server" -P "your_password"
```

### 6.2 发布测试消息

在另一个终端窗口中发布消息：

```bash
mosquitto_pub -h localhost -p 1883 -t "test/topic" -m "Hello AIPI system!" -u "aisa_server" -P "your_password"
```

如果配置正确，订阅窗口应该会显示发布的消息。

## 7. AIPI系统MQTT主题结构

AIPI系统使用以下MQTT主题结构进行通信：

### 7.1 设备通信

- `device/control`：向设备发送控制命令
- `device/{device_id}/data`：设备发布传感器数据
- `device/{device_id}/status`：设备发布状态信息

### 7.2 LangChain通信

- `langchain/process/{device_id}`：向特定设备发送自然语言命令
- `langchain/response/{device_id}`：设备返回自然语言处理结果

### 7.3 系统状态与监控

- `system/server/status`：服务器状态更新
- `system/alerts/{device_id}`：设备警报通知

## 8. 生产环境注意事项

### 8.1 防火墙配置

确保防火墙允许MQTT端口：

```bash
# 允许标准MQTT端口
sudo ufw allow 1883/tcp

# 如果使用TLS，允许安全MQTT端口
sudo ufw allow 8883/tcp

# 如果使用WebSockets，允许WebSockets端口
sudo ufw allow 9001/tcp
```

### 8.2 负载均衡

对于大规模部署，考虑使用MQTT集群或负载均衡：

- [EMQ X](https://www.emqx.io/)：高可用、高性能的MQTT集群解决方案
- [HiveMQ](https://www.hivemq.com/)：企业级MQTT消息平台

### 8.3 定期备份

定期备份Mosquitto配置和数据：

```bash
# 备份配置文件
sudo cp -r /etc/mosquitto /backup/mosquitto_config_$(date +%Y%m%d)

# 备份持久化数据（如果有）
sudo cp -r /var/lib/mosquitto /backup/mosquitto_data_$(date +%Y%m%d)
```

## 9. 故障排除

### 9.1 连接问题

如果无法连接到MQTT服务器：

- 检查服务状态：`sudo systemctl status mosquitto`
- 验证防火墙设置：`sudo ufw status`
- 查看日志文件：`sudo tail -f /var/log/mosquitto/mosquitto.log`

### 9.2 认证问题

如果认证失败：

- 确认用户名和密码正确
- 重新创建密码文件：`sudo mosquitto_passwd -c /etc/mosquitto/passwd username`
- 检查权限：`ls -la /etc/mosquitto/passwd`（确保文件权限正确）

### 9.3 性能问题

如果遇到性能问题：

- 调整最大连接数：在配置文件中添加 `max_connections 1000`
- 增加系统限制：`sudo nano /etc/security/limits.conf`
- 监控资源使用：`htop`、`netstat -an | grep 1883 | wc -l`

## 10. 监控MQTT服务器

### 10.1 设置监控服务

可以使用以下工具监控MQTT服务器：

- [MQTT Explorer](http://mqtt-explorer.com/)：图形化MQTT客户端，用于调试和监控
- [Prometheus](https://prometheus.io/) + [Mosquitto Exporter](https://github.com/sapcc/mosquitto-exporter)：用于收集指标
- [Grafana](https://grafana.com/)：用于可视化指标和创建仪表板

### 10.2 设置警报

为重要指标设置警报：

- 连接失败率
- 高消息吞吐量
- 服务器资源使用率
- 异常连接模式

## 11. 进一步资源

- [Mosquitto官方文档](https://mosquitto.org/documentation/)
- [MQTT规范](https://mqtt.org/mqtt-specification/)
- [MQTT安全实践指南](https://www.hivemq.com/mqtt-security-fundamentals/) 
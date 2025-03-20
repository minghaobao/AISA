# AI命令执行系统使用指南

本文档提供了AI命令执行系统的详细使用说明，帮助您理解如何与系统交互，并充分利用其功能。

## 系统概述

AI命令执行系统由以下几个主要组件组成：

1. **服务器端**:
   - 运行LangChain命令代理
   - 处理自然语言请求转换为命令
   - 通过MQTT发送命令并接收结果

2. **设备端**:
   - 在树莓派或其他设备上运行
   - 接收命令并执行
   - 返回执行结果
   - 定期发送状态更新

3. **MQTT服务器**:
   - 在服务器端和设备端之间传递消息
   - 支持多设备并行通信

## 准备工作

在开始使用前，确保完成以下步骤：

1. 按照[MQTT服务器部署指南](mqtt_server_setup.md)配置了MQTT服务器
2. 按照[树莓派安装指南](raspberry_pi_installation.md)或Windows安装说明配置了设备
3. 已获取OpenAI API密钥（用于LangChain和AI功能）

## 基本使用流程

### 1. 启动设备端命令执行器

在树莓派或设备上运行：

```bash
python ai_mqtt_langchain/rpi_command_executor.py
```

如果您已配置系统服务，它应该已自动启动。

您可以检查设备端日志确认其是否正在运行：

```bash
sudo journalctl -u rpi-command-executor.service -f
```

### 2. 使用AI命令助手

在服务器端运行：

```bash
python ai_mqtt_langchain/langchain_command_agent.py --device-id rpi_001
```

系统将提示您输入问题或命令。例如：

```
请输入您的问题或命令: 检查树莓派的CPU温度和内存使用情况
```

AI将分析您的请求，选择适当的Linux命令，发送到设备执行，并向您返回结果。

### 3. 直接发送命令（不使用AI）

如果您想直接发送特定命令而不经过AI处理，可以使用命令发送工具：

```bash
python ai_mqtt_langchain/send_rpi_command.py --device-id rpi_001 --command "free -h && vcgencmd measure_temp"
```

这将直接发送指定的命令到设备，并显示执行结果。

## 常用命令示例

以下是一些您可以通过系统执行的常用命令示例：

### 系统信息

**自然语言请求**：
```
请告诉我树莓派的系统信息
```

**AI可能执行的命令**：
```bash
uname -a && cat /etc/os-release
```

### 资源使用情况

**自然语言请求**：
```
树莓派的资源使用情况如何？
```

**AI可能执行的命令**：
```bash
free -h && vcgencmd measure_temp && df -h && top -bn1 | head -15
```

### 网络连接

**自然语言请求**：
```
检查树莓派的网络连接
```

**AI可能执行的命令**：
```bash
ifconfig && ping -c 4 8.8.8.8 && netstat -tuln
```

### 文件操作

**自然语言请求**：
```
在桌面创建一个文件并写入当前日期
```

**AI可能执行的命令**：
```bash
echo "Current date: $(date)" > ~/Desktop/date_file.txt && cat ~/Desktop/date_file.txt
```

## 高级用法

### 多轮对话

AI命令助手支持多轮对话。例如：

```
用户: 查看当前目录下的文件
AI: [执行 ls -la 命令并显示结果]

用户: 创建一个名为test的目录
AI: [执行 mkdir test 命令]

用户: 进入这个目录并创建一个文件
AI: [执行 cd test && touch sample.txt 命令]
```

AI会记住之前的对话内容，因此可以理解上下文相关的指令。

### 使用多个设备

您可以同时连接多个设备，只需在命令中指定不同的设备ID：

```bash
# 运行命令助手连接到设备1
python ai_mqtt_langchain/langchain_command_agent.py --device-id rpi_001

# 另一个终端窗口中，连接到设备2
python ai_mqtt_langchain/langchain_command_agent.py --device-id rpi_002
```

在对话中，AI将知道您正在与哪个设备交互。

### 定时任务

您可以使用系统设置定时任务。例如：

**自然语言请求**：
```
设置每小时记录一次CPU温度到日志文件
```

**AI可能执行的命令**：
```bash
(crontab -l 2>/dev/null; echo "0 * * * * /usr/bin/vcgencmd measure_temp >> /home/pi/temp_log.txt") | crontab -
```

## 安全注意事项

使用本系统时，请注意以下安全事项：

1. **命令限制**: 默认情况下，系统可以执行任何命令。在生产环境中，应考虑限制可执行的命令范围。

2. **加密通信**: 在公共网络上使用时，应配置MQTT服务器使用TLS加密。

3. **认证**: 始终为MQTT服务器启用用户名/密码认证。

4. **设备权限**: 避免让命令执行器以root用户运行，创建权限有限的专用用户。

5. **API密钥保护**: 妥善保管OpenAI API密钥，不要将其硬编码在代码中。

## 故障排除

### 设备不响应命令

1. 检查MQTT连接:
   ```bash
   mosquitto_sub -h <MQTT服务器地址> -t "device/#" -v
   ```

2. 验证设备ID是否正确
   ```bash
   # 检查设备配置文件
   cat ai_mqtt_langchain/rpi_executor_config.json
   ```

3. 检查设备端日志
   ```bash
   sudo journalctl -u rpi-command-executor.service -n 50
   ```

### AI无法正确理解请求

1. 尝试使用更具体的语言描述您的需求
2. 提供更多上下文信息
3. 使用简单明确的指令

### 命令执行超时

对于长时间运行的命令，可以增加超时设置：

```bash
python ai_mqtt_langchain/send_rpi_command.py --device-id rpi_001 --command "find / -name '*.log'" --timeout 180
```

## 扩展系统

您可以通过以下方式扩展系统功能：

1. **添加自定义工具**: 修改`langchain_command_agent.py`添加新的LangChain工具
2. **集成传感器数据**: 修改树莓派代码以收集和报告传感器数据
3. **创建Web界面**: 开发Web前端替代命令行界面
4. **添加数据分析功能**: 将系统与数据存储和分析工具集成

## 更多资源

- 阅读[项目README](../README.md)获取完整项目概述
- 查阅[MQTT服务器部署指南](mqtt_server_setup.md)了解通信配置
- 参考[树莓派安装指南](raspberry_pi_installation.md)获取设备配置详情 
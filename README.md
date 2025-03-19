# AI 远程命令执行系统

这是一个基于LangChain和MQTT的系统，允许AI助手通过自然语言分析并生成命令，远程执行到树莓派等设备上。系统支持在Linux、Windows和macOS平台上运行。

## 功能特点

- 🤖 **AI命令生成**: 使用LangChain和OpenAI模型将用户自然语言请求转换为设备命令
- 🔄 **实时通信**: 通过MQTT协议实现设备与服务器之间的实时双向通信
- 🛠️ **远程命令执行**: 在树莓派等远程设备上执行Linux命令并获取结果
- 🔍 **状态监控**: 定期发送设备状态和资源使用情况到服务器
- 🔐 **安全通信**: 支持MQTT认证和加密通信
- 📊 **交互式界面**: 命令行交互式接口，方便进行对话式命令生成
- 💻 **跨平台支持**: 支持在Linux、Windows和macOS平台上运行

## 系统架构

系统由以下几个主要组件组成：

- **LangChain命令代理**: 负责分析用户自然语言请求并生成适当的设备命令
- **MQTT通信层**: 处理服务器与设备之间的消息传递
- **命令执行器**: 在设备（如树莓派）上运行，接收并执行命令，返回结果
- **命令发送工具**: 用于手动向设备发送命令并查看结果

## 安装指南

### MQTT服务器配置

在使用系统之前，您需要配置MQTT服务器。请参阅详细的[MQTT服务器部署指南](docs/mqtt_server_setup.md)，其中包含以下内容：

- 在不同平台(Linux/Windows/Docker)上安装Mosquitto
- 配置安全访问和TLS加密
- 测试MQTT服务器
- 防火墙配置
- 性能优化与故障排除

### 服务器端

1. 克隆仓库:
   ```bash
   git clone https://github.com/yourusername/ai-command-system.git
   cd ai-command-system
   ```

2. 安装依赖:
   ```bash
   pip install -r requirements.txt
   ```

   在Windows系统上，可能需要额外安装:
   ```bash
   pip install pywin32 wmi
   ```

3. 配置环境变量:
   ```bash
   cp ai_mqtt_langchain/.env.example ai_mqtt_langchain/.env
   # 编辑.env文件，设置OpenAI API密钥和MQTT配置
   ```

### 树莓派/Linux设备端

请参阅详细的[树莓派安装指南](docs/raspberry_pi_installation.md)。

简要步骤:
1. 克隆仓库
2. 安装依赖 (`paho-mqtt`, `psutil`)
3. 配置设备
4. 设置自启动服务

### Windows设备端

1. 克隆仓库:
   ```bash
   git clone https://github.com/yourusername/ai-command-system.git
   cd ai-command-system
   ```

2. 安装依赖:
   ```bash
   pip install paho-mqtt psutil pywin32 wmi
   ```

3. 配置设备:
   ```bash
   copy ai_mqtt_langchain\rpi_executor_config.json.example ai_mqtt_langchain\rpi_executor_config.json
   # 编辑配置文件，设置设备ID和MQTT连接信息
   ```

## 使用方法

请查阅详细的[使用指南](docs/usage_guide.md)了解系统的完整使用方法和示例。以下是基本使用步骤：

### 启动树莓派命令执行器

在树莓派上运行:

```bash
python ai_mqtt_langchain/rpi_command_executor.py
```

### 手动发送命令

使用命令行工具发送指定命令:

```bash
python ai_mqtt_langchain/send_rpi_command.py --device-id rpi_sensor_001 --command "ls -la"
```

### 使用AI命令助手

运行交互式AI命令助手:

```bash
python ai_mqtt_langchain/langchain_command_agent.py --device-id rpi_sensor_001 --openai-api-key YOUR_API_KEY
```

然后，您可以通过自然语言与AI交互，例如:
- "查看树莓派上的CPU使用情况"
- "列出/home目录中的文件"
- "检查网络连接状态"

AI将分析您的请求，生成适当的Linux命令，发送到设备执行，并返回结果。

## 项目结构

```
ai_mqtt_langchain/
├── langchain_command_agent.py  # AI命令生成代理
├── rpi_command_executor.py     # 树莓派命令执行器
├── send_rpi_command.py         # 命令发送工具
├── rpi_executor_config.json    # 树莓派配置文件
└── .env.example                # 环境变量示例
```

## 配置选项

### 环境变量

关键配置参数在`.env`文件中设置:

- `OPENAI_API_KEY`: OpenAI API密钥
- `MQTT_HOST`: MQTT代理服务器地址
- `MQTT_PORT`: MQTT代理服务器端口
- `DEVICE_IDS`: 可用设备ID列表

### 树莓派配置

树莓派配置在`rpi_executor_config.json`文件中:

- `device_id`: 设备唯一标识符
- `mqtt_host`: MQTT代理服务器地址
- `mqtt_port`: MQTT代理服务器端口
- `heartbeat_interval`: 设备状态报告间隔（秒）

## 开发指南

### 添加新的命令工具

1. 在`langchain_command_agent.py`文件中，添加新的Tool定义
2. 提供工具名称、函数和描述
3. 将工具添加到代理的工具列表中

### 自定义命令处理

修改`rpi_command_executor.py`中的`execute_command`方法以添加自定义命令处理逻辑。

## 安全注意事项

- 避免在公共网络上使用不带TLS的MQTT连接
- 始终使用MQTT用户名/密码认证
- 限制设备可执行的命令范围，避免授予root权限
- 定期审查命令执行日志

## 许可证

[MIT许可证](LICENSE)

## 联系方式

如有问题或建议，请联系：your.email@example.com

## 文档索引

系统提供了详细的文档指南：

- [MQTT服务器部署指南](docs/mqtt_server_setup.md) - 如何在不同平台上配置MQTT服务
- [树莓派安装指南](docs/raspberry_pi_installation.md) - 在树莓派上设置命令执行器
- [使用指南](docs/usage_guide.md) - 系统的基本和高级使用方法
- [LangChain配置与本地服务启动](docs/langchain_setup.md) - AI配置和服务启动详解

## 快速启动

本系统提供了简便的启动脚本，可一键启动所有必要服务：

### Linux/macOS用户

```bash
# 添加执行权限
chmod +x start_system.sh

# 运行启动脚本
./start_system.sh
```

### Windows用户

```
# 双击运行，或在命令提示符中执行
start_system.bat
```

启动脚本会自动：
1. 检查环境配置和必要依赖
2. 启动MQTT服务器（如果未运行）
3. 启动LangChain命令代理
4. 提供设备选择界面（如配置了多个设备）

详细的配置说明请参考[LangChain配置与本地服务启动](docs/langchain_setup.md)文档。 
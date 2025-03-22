# 树莓派AI命令控制中心 - Web界面

这是一个基于Flask的Web界面，用于远程控制和监控树莓派设备。通过自然语言输入，结合LangChain和MQTT，实现对树莓派的智能化命令控制。

## 功能特点

- 基于LangChain的自然语言命令处理
- 实时MQTT通信
- 响应式Web界面设计
- 实时设备状态监控
- 直观的命令输入和结果显示

## 安装要求

- Python 3.7+
- Flask
- LangChain
- OpenAI API密钥
- MQTT服务器

## 快速开始

### Windows系统

1. 双击运行 `start_web.bat`
2. 或在命令行中执行:
   ```
   cd ai_mqtt_langchain/web
   python start_web.py
   ```

### Linux/macOS系统

1. 使脚本可执行:
   ```
   chmod +x start_web.sh
   ```
2. 运行脚本:
   ```
   ./start_web.sh
   ```
3. 或直接启动:
   ```
   python3 start_web.py
   ```

## 配置

通过`.env`文件或环境变量配置以下参数:

```
# OpenAI API配置
OPENAI_API_KEY=your_api_key_here

# MQTT配置
MQTT_HOST=localhost
MQTT_PORT=1883
MQTT_USERNAME=
MQTT_PASSWORD=

# 设备配置
DEVICE_ID=rpi_001
```

## 使用方法

1. 在浏览器中访问: `http://localhost:5000`
2. 在文本框中输入自然语言命令，例如:
   - "查看系统运行状态"
   - "检查CPU温度"
   - "列出根目录下的文件"
   - "显示网络连接状态"
3. 点击"执行"按钮，等待命令结果显示

## 自定义和扩展

- 修改`app.py`中的系统提示调整AI响应
- 扩展`execute_command`工具添加更多功能
- 修改HTML/CSS调整界面设计

## 故障排除

1. **无法连接到MQTT服务器**
   - 确认MQTT服务器已启动
   - 检查MQTT主机地址和端口配置

2. **API密钥错误**
   - 确认已正确设置OPENAI_API_KEY环境变量
   - 检查API密钥是否有效

3. **命令执行超时**
   - 检查树莓派是否在线并连接到MQTT服务器
   - 验证命令执行器是否正常运行

## 注意事项

- 此Web界面默认绑定到所有网络接口(0.0.0.0)
- 生产环境下建议配置HTTPS和适当的认证机制
- 确保使用命令的安全性，避免执行危险操作 
# AIPI 系统文档

## 1. 系统概述

AIPI（AI-Powered IoT Platform）是一个基于人工智能的物联网控制系统，通过自然语言处理和MQTT通信，实现对树莓派设备的智能监控和控制。系统由服务器端和树莓派端两部分组成，支持多设备管理、数据存储分析、告警监控等功能。

### 1.1 系统架构

系统分为两个主要部分：

- **服务器端**：中央控制系统，负责数据处理、Web界面、LangChain自然语言处理和数据存储
- **树莓派端**：部署在各个树莓派设备上的客户端，负责硬件控制、数据采集和命令执行

通信基于MQTT协议，数据存储使用InfluxDB，数据可视化使用Grafana。

### 1.2 核心功能

- 设备数据收集与监控（CPU、内存、温度等系统参数）
- 基于LangChain的自然语言命令处理
- GPIO设备控制（继电器、风扇、灯光等）
- 告警监控与通知（邮件、Telegram）
- 数据存储与分析（InfluxDB + Grafana）
- Web管理界面

## 2. 安装指南

### 2.1 服务器端安装

#### 环境要求
- Python 3.8+
- MQTT代理（如Mosquitto）
- InfluxDB 2.0+
- Grafana（可选，用于数据可视化）

#### 安装步骤

1. 克隆代码库：
```bash
git clone https://github.com/yourusername/AIPI.git
cd AIPI/server
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 复制并修改配置文件：
```bash
cp .env.example .env
# 编辑.env文件，设置必要的配置参数
```

4. 创建本地配置文件（可选，包含敏感信息）：
```bash
cp .env.example .env.local
# 编辑.env.local，添加API密钥等敏感信息
```

5. 启动服务器：
```bash
python run.py
```

### 2.2 树莓派端安装

#### 环境要求
- 树莓派OS
- Python 3.8+
- 适当连接的GPIO设备（继电器、传感器等）

#### 安装步骤

1. 克隆代码库：
```bash
git clone https://github.com/yourusername/AIPI.git
cd AIPI/raspberry_pi
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 复制并修改配置文件：
```bash
cp .env.example .env
# 编辑.env文件，设置必要的配置参数
```

4. 创建本地设备配置：
```bash
cp .env.example .env.local
# 编辑.env.local，根据硬件配置设置GPIO引脚等
```

5. 启动树莓派客户端：
```bash
python rpi_run.py
```

### 2.3 Web界面安装

Web界面已包含在服务器端，不需要单独安装。若要单独运行Web界面：

```bash
cd AIPI/server/web
python start_web.py
```

详细安装说明，请参阅：
- [服务器安装详细指南](docs/server_installation.md)
- [树莓派安装详细指南](docs/raspberry_pi_installation.md)
- [MQTT服务器设置](docs/mqtt_server_setup.md)

## 3. 使用指南

### 3.1 服务器管理

#### 启动服务
```bash
# 完整启动服务器（MQTT、Web、LangChain、告警等）
python run.py

# 单独启动Web服务
python web/start_web.py
```

#### 监控与管理
- 访问Web界面：`http://<服务器IP>:5000`
- 查看数据可视化：`http://<服务器IP>:3000`（Grafana）
- 检查日志：`logs/server.log`和`logs/alerts.log`

### 3.2 树莓派设备控制

#### 启动设备客户端
```bash
# 启动所有服务
python rpi_run.py

# 只启动MQTT客户端
python rpi_run.py --mqtt

# 只启动设备控制器
python rpi_run.py --device

# 只启动LangChain处理器
python rpi_run.py --processor
```

#### 自然语言命令示例

通过Web界面或MQTT发送自然语言命令：

- "打开客厅的灯"
- "将风扇速度调到50%"
- "监控服务器CPU温度，如果超过70度发送警报"
- "每天晚上10点关闭所有设备"

详细使用说明，请参阅：
- [使用指南](docs/usage_guide.md)
- [LangChain设置与使用](docs/langchain_setup.md)

## 4. 项目结构

```
AIPI/
├── server/                # 服务器端
│   ├── web/               # Web界面
│   │   ├── routes/        # Web路由
│   │   ├── templates/     # HTML模板
│   │   ├── __init__.py    # Web初始化
│   │   └── start_web.py   # Web启动脚本
│   ├── config.py          # 服务器配置
│   ├── mqtt_client.py     # MQTT客户端
│   ├── langchain_processor.py # LangChain处理器
│   ├── influx_writer.py   # InfluxDB写入
│   ├── alert_manager.py   # 告警管理
│   └── run.py             # 服务器启动脚本
│
├── raspberry_pi/          # 树莓派端
│   ├── config.py          # 树莓派配置
│   ├── mqtt_client.py     # MQTT客户端
│   ├── command_executor.py # 命令执行器
│   ├── device_controller.py # 设备控制
│   ├── langchain_processor.py # LangChain处理器
│   └── rpi_run.py         # 树莓派启动脚本
│
└── docs/                  # 文档
    ├── server_installation.md   # 服务器安装指南
    ├── raspberry_pi_installation.md  # 树莓派安装指南
    ├── mqtt_server_setup.md    # MQTT服务器设置
    ├── usage_guide.md          # 使用指南
    └── langchain_setup.md      # LangChain设置
```

## 5. 故障排除

### 常见问题

1. **MQTT连接失败**
   - 检查MQTT代理是否运行
   - 验证MQTT用户名和密码
   - 确认防火墙未阻止MQTT端口

2. **OpenAI API错误**
   - 验证API密钥是否有效
   - 检查API请求限制
   - 查看OpenAI服务状态

3. **树莓派GPIO错误**
   - 确认GPIO引脚配置正确
   - 检查硬件连接
   - 验证运行权限（可能需要sudo）

4. **InfluxDB连接问题**
   - 确认InfluxDB服务运行
   - 验证令牌和组织配置
   - 检查存储桶是否存在

### 日志文件
- 服务器日志：`logs/server.log`
- 告警日志：`logs/alerts.log`
- 树莓派日志：`raspberry_pi.log`

## 6. 贡献指南

欢迎贡献代码、报告问题或提出改进建议。请遵循以下步骤：

1. Fork本仓库
2. 创建您的特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交您的更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 打开一个Pull Request

## 7. 许可证

本项目采用MIT许可证 - 详见 [LICENSE](LICENSE) 文件

## 8. 联系方式

项目维护者 - [@yourname](https://github.com/yourname) - email@example.com

项目链接：[https://github.com/yourusername/AIPI](https://github.com/yourusername/AIPI) 
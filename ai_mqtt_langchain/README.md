# AI智能监控平台

基于MQTT、LangChain和InfluxDB的智能设备监控与控制平台。

## 功能特点

- 实时设备数据采集与监控
- 智能告警管理
- 设备远程控制
- 数据可视化
- 语音交互
- 多设备支持

## 系统架构

- MQTT: 设备通信
- InfluxDB: 时序数据存储
- Grafana: 数据可视化
- LangChain: AI智能控制
- Flask: Web后端
- Next.js: Web前端

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 16+
- Docker & Docker Compose
- MQTT Broker
- InfluxDB 2.x
- Grafana 9.x

### 安装步骤

1. 克隆代码库:
```bash
git clone https://github.com/yourusername/ai-mqtt-langchain.git
cd ai-mqtt-langchain
```

2. 安装Python依赖:
```bash
pip install -r requirements.txt
```

3. 配置环境变量:
```bash
cp .env.example .env
# 编辑.env文件,填入必要的配置信息
```

4. 启动服务:
```bash
# 使用Docker Compose启动所有服务
docker-compose up -d

# 或手动启动各个服务
python run.py --mqtt
python run.py --web
python run.py --alert
```

### 访问服务

- Web界面: http://localhost:3000
- Grafana: http://localhost:3001
- InfluxDB: http://localhost:8086

## 项目结构

```
ai-mqtt-langchain/
├── ai_mqtt_langchain/        # Python后端
│   ├── __init__.py
│   ├── config.py            # 配置文件
│   ├── mqtt_client.py       # MQTT客户端
│   ├── device_control.py    # 设备控制
│   ├── alert_check.py       # 告警检查
│   ├── web_control.py       # Web控制
│   └── run.py              # 主程序
├── nextjs_frontend/         # Next.js前端
├── docker/                  # Docker配置
├── grafana/                 # Grafana配置
├── tests/                   # 测试用例
├── .env                     # 环境变量
├── requirements.txt         # Python依赖
├── docker-compose.yml       # Docker编排
└── README.md               # 项目说明
```

## 配置说明

### MQTT配置

```python
MQTT_CONFIG = {
    "host": "localhost",
    "port": 1883,
    "username": "your_username",
    "password": "your_password",
    "topics": {
        "data": "devices/+/data",
        "control": "devices/+/control",
        "status": "devices/+/status"
    }
}
```

### 设备配置

```python
DEVICE_CONFIG = {
    "relay": {
        "pin": 17,
        "initial_state": "off"
    },
    "fan": {
        "pin": 18,
        "initial_state": "off"
    }
}
```

### 告警配置

```python
ALERT_CONFIG = {
    "cooldown": 300,  # 告警冷却时间(秒)
    "check_interval": 60,  # 检查间隔(秒)
    "rules": {
        "temperature": {
            "warning": 25,
            "critical": 30
        },
        "humidity": {
            "warning": 70,
            "critical": 80
        }
    }
}
```

## 开发指南

### 添加新设备

1. 在`device_control.py`中添加设备类
2. 在`config.py`中添加设备配置
3. 在`web_control.py`中添加控制接口

### 添加新告警规则

1. 在`alert_check.py`中添加规则检查函数
2. 在`config.py`中添加规则配置
3. 在`web_control.py`中添加告警接口

### 添加新可视化面板

1. 在Grafana中创建新面板
2. 导出面板配置到`grafana_dashboard.json`
3. 更新`docker-compose.yml`中的Grafana配置

## 测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_device_control.py

# 生成测试覆盖率报告
pytest --cov=ai_mqtt_langchain
```

## 部署

### Docker部署

```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

### 手动部署

1. 安装依赖
2. 配置环境变量
3. 启动各个服务
4. 配置反向代理(可选)

## 监控与维护

### 日志

- 应用日志: `logs/app.log`
- 告警日志: `logs/alert.log`
- MQTT日志: `logs/mqtt.log`

### 备份

```bash
# 运行备份脚本
./backup.sh
```

### 监控指标

- CPU使用率
- 内存使用率
- 磁盘使用率
- MQTT连接状态
- 设备在线状态

## 贡献指南

1. Fork项目
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建Pull Request

## 许可证

MIT License

## 联系方式

- 项目主页: https://github.com/yourusername/ai-mqtt-langchain
- 问题反馈: https://github.com/yourusername/ai-mqtt-langchain/issues
- 邮件联系: your.email@example.com 
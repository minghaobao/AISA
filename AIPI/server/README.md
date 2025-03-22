# AISA智能物联网服务平台

AISA是一个集成了AI能力的物联网服务平台，支持设备管理、数据可视化和智能控制功能。

## 功能特点

- **设备管理**：添加、编辑和删除IoT设备
- **数据可视化**：通过Grafana展示设备数据图表和仪表盘
- **AI控制**：通过自然语言与设备进行交互
- **实时监控**：监控设备状态和性能数据
- **告警管理**：配置和管理设备告警

## 系统要求

- Python 3.7+
- Flask
- paho-mqtt
- langchain
- InfluxDB (用于数据存储)
- Grafana (用于数据可视化)

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

在项目根目录创建`.env`文件，包含以下配置：

```
# OpenAI API配置
OPENAI_API_KEY=your_api_key
OPENAI_MODEL=gpt-3.5-turbo

# MQTT配置
MQTT_HOST=localhost
MQTT_PORT=1883
DEVICE_ID=your_device_id

# 数据库配置
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=your_token
INFLUXDB_ORG=your_org
INFLUXDB_BUCKET=iot_data

# Grafana配置
GRAFANA_URL=http://localhost:3000
```

### 3. 启动服务

使用提供的启动脚本：

```bash
./start_service.sh
```

或者使用更多参数：

```bash
./start_service.sh --port 5000 --model gpt-3.5-turbo --debug
```

### 4. 停止服务

使用停止脚本：

```bash
./stop_service.sh
```

## 访问服务

启动服务后，可以通过以下地址访问：

- Web界面：http://localhost:5000
- API接口：http://localhost:5000/api

## API文档

### 设备管理API

- `GET /api/devices/`: 获取所有设备列表
- `GET /api/devices/{device_id}`: 获取单个设备详情
- `POST /api/devices/`: 添加新设备
- `PUT /api/devices/{device_id}`: 更新设备信息
- `DELETE /api/devices/{device_id}`: 删除设备

### Grafana API

- `GET /grafana/dashboards`: 获取仪表盘列表
- `GET /grafana/view/{dashboard_uid}`: 查看仪表盘
- `POST /grafana/import`: 导入仪表盘

### 状态API

- `GET /api/status`: 获取API服务状态

## 故障排除

### 服务无法启动

1. 检查依赖是否安装完整：`pip list | grep <package_name>`
2. 检查环境变量配置是否正确
3. 查看日志文件：`service.log`

### API请求失败

1. 确认服务是否正在运行：`ps aux | grep integrated_server.py`
2. 检查API路由是否正确：访问 `/debug/routes` 查看所有注册的路由
3. 查看日志文件了解详细错误信息

## 贡献指南

欢迎提交问题和功能请求！如果你想贡献代码，请遵循以下步骤：

1. Fork仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建Pull Request

## 许可证

该项目采用MIT许可证 - 详见[LICENSE](LICENSE)文件 
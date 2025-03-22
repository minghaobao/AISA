# AIPI系统使用指南

本指南将介绍如何使用AIPI系统进行设备监控、命令执行和数据分析。

## 1. 系统概述

AIPI是一个AI驱动的物联网平台，允许您通过自然语言管理和控制连接的树莓派设备。系统包括以下主要组件：

- **服务器端**：处理自然语言命令、存储数据和提供Web界面
- **树莓派客户端**：运行在设备上，执行命令并收集数据
- **MQTT中间件**：处理组件之间的通信

## 2. 系统启动

### 2.1 启动服务器

进入服务器目录并启动服务：

```bash
cd AIPI/server
python server_run.py
```

这将启动以下服务：
- MQTT客户端（用于通信）
- 数据收集服务（用于接收和存储设备数据）
- LangChain处理器（用于自然语言处理）
- Web服务器（用于Web界面）

### 2.2 启动API服务器

如果只需要API服务，可以单独启动：

```bash
cd AIPI/server
python api-web.py
```

这将启动轻量级API服务器，提供设备控制和数据访问的接口。

### 2.3 启动树莓派客户端

在每个树莓派设备上，运行：

```bash
cd AIPI/raspberry_pi
python rpi_run.py
```

这将启动以下服务：
- MQTT客户端（用于通信）
- 设备控制器（用于GPIO控制）
- 数据收集服务（用于收集设备数据）
- LangChain处理器（用于本地处理命令）

## 3. Web界面使用

Web界面是管理和监控设备的主要方式。

### 3.1 访问Web界面

在浏览器中访问：
```
http://服务器IP地址:5000
```

默认登录凭据：
- 用户名：`admin@aipi.system`
- 密码：`admin`（请在首次登录后更改）

### 3.2 使用API接口

API服务器提供以下主要接口：

```
# 获取API状态
GET http://服务器IP地址:5000/api/status

# 登录认证
POST http://服务器IP地址:5000/api/login
Body: {"username": "user@example.com", "password": "password"}

# 获取设备列表
GET http://服务器IP地址:5000/api/devices

# 获取特定设备信息
GET http://服务器IP地址:5000/api/devices/{device_id}

# 控制设备
POST http://服务器IP地址:5000/api/devices/{device_id}/control
Body: {"action": "on", "parameters": {}}

# 获取设备历史数据
GET http://服务器IP地址:5000/api/devices/{device_id}/history?start={timestamp}&end={timestamp}

# 获取系统监控数据
GET http://服务器IP地址:5000/api/monitor
```

所有API请求（除了登录）都需要在请求头中包含JWT令牌：
```
Authorization: Bearer {token}
```

### 3.3 仪表板

仪表板显示：
- 设备状态概览
- 最近警报
- 系统性能指标
- 设备数据图表

### 3.4 设备管理

在设备页面，您可以：
- 查看所有注册设备
- 检查各设备状态（在线/离线）
- 查看详细设备信息（CPU、内存、温度等）
- 向设备发送控制命令

### 3.5 命令控制中心

命令控制中心允许您：
- 使用自然语言发送命令到特定设备
- 查看命令执行历史
- 创建和保存常用命令模板

示例命令：
- "打开客厅的灯"
- "关闭所有设备的继电器"
- "将风扇速度设置为50%"
- "报告厨房设备的温度"
- "每小时执行一次系统状态检查"

### 3.6 数据分析

数据分析页面提供：
- 设备历史数据图表
- 性能趋势分析
- 自定义报告生成
- 数据导出功能

## 4. 命令语法

您可以通过Web界面或直接通过MQTT发送命令。

### 4.1 设备控制命令

基本设备命令使用以下JSON格式：

```json
{
  "device_id": "设备ID",
  "action": "动作名称",
  "parameters": {
    "参数名1": "参数值1",
    "参数名2": "参数值2"
  }
}
```

常用命令示例：

**打开继电器**
```json
{
  "device_id": "raspberry_pi_001",
  "action": "gpio_control",
  "parameters": {
    "pin": "relay_1",
    "state": "on"
  }
}
```

**设置风扇速度**
```json
{
  "device_id": "raspberry_pi_001",
  "action": "gpio_control",
  "parameters": {
    "pin": "fan_1",
    "pwm": 75
  }
}
```

**读取传感器**
```json
{
  "device_id": "raspberry_pi_001",
  "action": "read_sensor",
  "parameters": {
    "sensor": "temperature"
  }
}
```

### 4.2 自然语言命令

当使用LangChain处理器时，您可以发送自然语言命令：

```json
{
  "query": "打开客厅的灯",
  "device_id": "raspberry_pi_001"
}
```

系统将解析命令并执行相应操作。支持的命令类型：
- 设备控制（开关灯、调节风扇等）
- 传感器读取（获取温度、湿度等）
- 状态查询（检查设备状态、网络连接等）
- 定时任务（设置定时操作）
- 条件控制（基于传感器值执行动作）

### 4.3 通过MQTT直接发送命令

使用任何MQTT客户端（如MQTT Explorer或mosquitto_pub）：

```bash
# 设备控制命令
mosquitto_pub -h mqtt服务器地址 -t "device/control" -m '{"device_id":"raspberry_pi_001","action":"gpio_control","parameters":{"pin":"relay_1","state":"on"}}'

# 自然语言命令
mosquitto_pub -h mqtt服务器地址 -t "langchain/process/raspberry_pi_001" -m '{"query":"打开厨房的灯","device_id":"raspberry_pi_001"}'
```

## 5. 数据收集

AIPI系统会自动收集设备数据。

### 5.1 收集的数据类型

- **系统数据**：
  - CPU使用率
  - 内存使用率
  - 磁盘使用率
  - 网络流量
  - 系统温度

- **传感器数据**（取决于连接的传感器）：
  - 温度和湿度（DHT传感器）
  - 光照强度
  - 运动检测
  - 自定义传感器数据

### 5.2 数据存储

数据存储在InfluxDB中，使用以下信息：
- 数据库：`aipi_metrics`
- 测量：`device_metrics`
- 标签：`device_id`、`metric_type`

### 5.3 数据查询示例

通过Web界面或直接使用InfluxDB查询语言：

```
SELECT mean("value") FROM "aipi_metrics"."autogen"."device_metrics" 
WHERE ("device_id" = 'raspberry_pi_001' AND "metric_type" = 'temperature') 
AND time >= now() - 24h 
GROUP BY time(30m) FILL(null)
```

## 6. 警报系统

AIPI系统包含警报功能，监控设备状态并在发生异常时通知您。

### 6.1 警报类型

- **系统警报**：
  - 高CPU使用率（>80%）
  - 高内存使用率（>90%）
  - 高温警报（>75℃）
  - 磁盘空间不足（<10%）
  - 设备离线

- **传感器警报**：
  - 温度超出阈值
  - 湿度超出阈值
  - 其他传感器阈值警报

### 6.2 警报配置

在Web界面的"警报设置"页面，您可以：
- 启用/禁用特定警报
- 配置警报阈值
- 设置通知方式（邮件、Telegram等）
- 创建自定义警报规则

### 6.3 警报通知

警报可通过以下方式接收：
- Web界面提醒
- 电子邮件
- Telegram消息
- 自定义Webhook

## 7. 定时任务

### 7.1 创建定时任务

在Web界面的"定时任务"页面：
1. 点击"新建任务"
2. 选择设备
3. 输入命令（JSON格式或自然语言）
4. 设置执行计划（一次性或重复）
5. 保存任务

### 7.2 查看和管理任务

- 查看所有计划任务
- 启用/禁用特定任务
- 编辑现有任务
- 查看任务执行历史和结果

## 8. 用户权限管理

### 8.1 用户角色

系统支持以下用户角色：
- **管理员**：完全访问权限
- **操作员**：可以控制设备和查看数据
- **查看者**：只能查看数据和状态

### 8.2 管理用户

管理员可以：
- 创建新用户
- 设置用户角色
- 重置用户密码
- 禁用用户账户

## 9. API集成

AIPI系统提供REST API，允许与第三方系统集成。

### 9.1 认证

使用JWT认证：

```bash
# 获取访问令牌
curl -X POST http://服务器IP地址:5000/api/auth/login -d '{"email":"admin@aipi.system","password":"admin"}'

# 使用令牌
curl -X GET http://服务器IP地址:5000/api/devices -H "Authorization: Bearer {your_token}"
```

### 9.2 主要API端点

- `/api/devices`：获取设备列表
- `/api/devices/{device_id}`：获取特定设备信息
- `/api/devices/{device_id}/control`：控制设备
- `/api/data`：查询历史数据
- `/api/alerts`：获取和管理警报

## 10. 故障排除

### 10.1 设备离线

如果设备显示为离线：
1. 确认树莓派已通电并运行
2. 检查网络连接
3. 验证MQTT服务器配置正确
4. 查看树莓派客户端日志（`raspberry_pi.log`）
5. 重启树莓派客户端服务

### 10.2 命令执行失败

如果命令无法执行：
1. 检查命令格式（JSON语法）
2. 确认设备支持该命令
3. 验证命令参数是否正确
4. 查看服务器日志（`server.log`）
5. 检查设备端LangChain处理器日志

### 10.3 数据不显示

如果设备数据未显示：
1. 确认数据收集已启用
2. 验证InfluxDB连接配置
3. 检查数据收集间隔设置
4. 查看数据收集服务日志
5. 重启服务器数据服务

### 10.4 Web界面问题

如果Web界面无法访问或显示错误：
1. 确认Web服务正在运行
2. 检查端口配置（默认5000）
3. 验证浏览器兼容性（推荐Chrome或Firefox）
4. 清除浏览器缓存
5. 检查Web服务器日志

## 11. 最佳实践

### 11.1 系统维护

- 定期备份数据库
- 更新软件包（`pip install -r requirements.txt --upgrade`）
- 监控磁盘空间和系统资源
- 定期重启服务以避免内存泄漏

### 11.2 安全建议

- 更改所有默认密码
- 启用MQTT认证和加密
- 使用HTTPS保护Web界面
- 定期审查用户权限
- 限制设备控制权限

### 11.3 性能优化

- 调整数据收集间隔
- 配置InfluxDB数据保留策略
- 使用数据降采样提高查询性能
- 增加服务器资源（内存和CPU）以处理更多设备 
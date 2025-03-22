# AIPI系统架构与开发文档

本文档详细描述AIPI系统的架构设计、组件功能和开发指南，帮助开发者理解系统结构并进行扩展开发。

## 系统架构概述

AIPI系统采用分层架构设计，包括以下主要层次：

1. **前端层**：提供Web界面和API端点，用于用户交互和系统管理
2. **API层**：RESTful API服务，处理前端请求并与后端服务交互
3. **业务逻辑层**：处理设备管理、命令解析、自然语言处理等核心功能
4. **数据层**：管理数据存储、查询和持久化
5. **设备通信层**：通过MQTT协议与Raspberry Pi设备通信

系统主要分为服务器端和树莓派客户端两部分：

### 服务器端

- Web界面和API服务
- MQTT客户端（与设备通信）
- LangChain自然语言处理
- InfluxDB数据存储
- 告警管理服务

### 树莓派客户端

- MQTT客户端（与服务器通信）
- 命令执行器
- 设备控制服务（GPIO控制）
- 数据收集服务（传感器数据）

## 服务器端文件结构及功能

以下是服务器端核心文件的路径和功能描述：

| 文件路径 | 功能描述 |
|---------|----------|
| `server/run.py` | 主程序入口，启动所有服务器端组件 |
| `server/api-web.py` | API Web服务器，提供RESTful接口 |
| `server/config.py` | 配置管理，加载环境变量和系统配置 |
| `server/mqtt_client.py` | MQTT客户端，负责设备通信 |
| `server/langchain_processor.py` | 自然语言处理服务 |
| `server/alert_manager.py` | 告警管理和通知服务 |
| `server/device_manager.py` | 设备管理和控制服务 |
| `server/database/influxdb_client.py` | InfluxDB数据库客户端 |
| `server/web/app.py` | Web应用主程序，提供用户界面 |
| `server/web/static/` | 静态资源文件（CSS、JS等） |
| `server/web/templates/` | HTML模板文件 |

## Web前端文件

| 文件路径 | 功能描述 |
|---------|----------|
| `server/web/app.py` | Web应用入口点，Flask应用配置 |
| `server/web/templates/index.html` | 主页模板 |
| `server/web/templates/devices.html` | 设备管理页面 |
| `server/web/templates/monitor.html` | 系统监控页面 |
| `server/web/templates/alerts.html` | 告警页面 |
| `server/web/static/js/api.js` | API调用封装 |
| `server/web/static/js/devices.js` | 设备管理JavaScript |
| `server/web/static/js/charts.js` | 数据可视化图表 |
| `server/web/routes/auth.py` | 认证相关路由 |
| `server/web/routes/devices.py` | 设备管理路由 |
| `server/web/routes/api.py` | API路由转发 |

## API与前端交互

API服务器提供以下主要端点：

| 端点 | HTTP方法 | 描述 |
|-----|---------|------|
| `/api/status` | GET | 获取API状态 |
| `/api/login` | POST | 用户认证 |
| `/api/devices` | GET | 获取设备列表 |
| `/api/devices` | POST | 添加新设备 |
| `/api/devices/{id}` | GET | 获取特定设备信息 |
| `/api/devices/{id}` | PUT | 更新设备信息 |
| `/api/devices/{id}` | DELETE | 删除设备 |
| `/api/devices/{id}/control` | POST | 控制设备 |
| `/api/devices/{id}/history` | GET | 获取设备历史数据 |
| `/api/monitor` | GET | 获取系统监控数据 |
| `/api/alerts` | GET | 获取告警信息 |
| `/api/alerts/{id}/acknowledge` | POST | 确认告警 |
| `/api/langchain/process` | POST | 处理自然语言命令 |

Web前端通过JavaScript与API交互，主要包括：

1. 用户登录认证
2. 设备管理和控制
3. 数据监控和可视化
4. 告警管理和处理
5. 自然语言命令处理

## 数据流程

### 设备数据上报流程

1. 树莓派设备收集传感器数据
2. 通过MQTT发布数据到指定主题（`device/{device_id}/data`）
3. 服务器MQTT客户端接收数据
4. 数据被存储到InfluxDB
5. Web前端通过API查询数据并展示

### 命令执行流程

1. 用户通过Web界面发送命令
2. Web服务器将命令发送到API
3. API通过MQTT发布命令到设备主题（`device/control`）
4. 树莓派设备接收命令并执行
5. 执行结果通过MQTT返回到服务器
6. Web界面更新显示结果

### 自然语言处理流程

1. 用户输入自然语言命令
2. 命令通过API发送到LangChain处理器
3. LangChain处理器解析命令，识别意图和参数
4. 生成具体的设备控制命令
5. 命令通过MQTT发送到设备

## 关键组件交互

### Web前端与API交互

Web前端通过RESTful API与后端服务交互，主要使用以下模式：

1. **AJAX请求**：使用JavaScript Fetch API或Axios库发送HTTP请求
2. **JWT认证**：所有API请求在Header中包含JWT令牌
3. **实时更新**：使用WebSocket获取实时数据更新

### API与后端服务交互

API服务通过以下方式与后端服务交互：

1. **直接调用**：同一进程内的组件直接调用
2. **MQTT消息**：通过MQTT协议与设备通信
3. **数据库查询**：与InfluxDB交互获取数据
4. **外部API调用**：与LangChain组件交互处理自然语言

## 系统启动与配置

系统提供多种启动方式：

1. **完整服务启动**：运行`run.py`启动所有服务
   ```bash
   python server/run.py
   ```

2. **API服务独立启动**：单独运行API服务
   ```bash
   python server/api-web.py
   ```

3. **Web服务独立启动**：单独运行Web服务
   ```bash
   python server/web/app.py
   ```

系统配置通过环境变量文件（`.env`和`.env.local`）管理，主要配置项包括：

- 基本配置（日志级别、日志文件）
- MQTT配置（主机、端口、用户名、密码）
- 设备ID配置
- LLM配置（API密钥、模型）
- InfluxDB配置（URL、令牌、组织、存储桶）
- 告警配置（阈值、通知渠道）
- Web服务器配置（端口、主机）
- JWT认证配置（密钥、过期时间）

## 开发指南

### 添加新的API端点

1. 在`server/api-web.py`中添加新的路由
   ```python
   @app.route('/api/new_endpoint', methods=['GET'])
   def new_endpoint():
       # 实现端点逻辑
       return jsonify({'success': True, 'data': {...}})
   ```

2. 在API文档中添加新端点的说明

### 添加前端API调用

1. 在`server/web/static/js/api.js`中添加新的API调用函数
   ```javascript
   async function callNewEndpoint() {
       const response = await fetch('/api/new_endpoint', {
           method: 'GET',
           headers: {
               'Authorization': `Bearer ${getToken()}`
           }
       });
       return await response.json();
   }
   ```

2. 在前端页面中使用新函数

### 添加新设备支持

1. 在`server/device_manager.py`中添加新设备类型的支持
2. 扩展MQTT主题结构以适应新设备类型
3. 更新设备控制和数据处理逻辑

## 安全与认证

系统使用JWT（JSON Web Token）进行API认证，流程如下：

1. **登录流程**：
   - 用户提交用户名和密码到`/api/login`
   - 服务器验证凭据并生成JWT令牌
   - 令牌返回给客户端并存储在本地

2. **API认证**：
   - 客户端在每个API请求的Header中包含JWT令牌
   - 服务器验证令牌的有效性和过期时间
   - 验证通过后处理请求

3. **登出流程**：
   - 客户端调用`/api/logout`
   - 服务器将令牌加入黑名单
   - 客户端删除本地存储的令牌

## API接口详细说明

### 认证接口

#### 登录

- **URL**: `/api/login`
- **方法**: `POST`
- **功能**: 验证用户凭据并返回JWT令牌
- **请求体**:
  ```json
  {
    "username": "admin",
    "password": "your_password"
  }
  ```
- **响应**:
  ```json
  {
    "success": true,
    "data": {
      "token": "eyJhbGciOiJIUzI1...",
      "expires": 3600
    },
    "message": "登录成功"
  }
  ```

#### 登出

- **URL**: `/api/logout`
- **方法**: `POST`
- **功能**: 使当前JWT令牌失效
- **响应**:
  ```json
  {
    "success": true,
    "message": "登出成功"
  }
  ```

### 设备管理接口

#### 获取设备列表

- **URL**: `/api/devices`
- **方法**: `GET`
- **功能**: 获取所有注册设备的列表
- **响应**:
  ```json
  {
    "success": true,
    "data": {
      "devices": [
        {
          "id": "rpi-001",
          "name": "客厅树莓派",
          "type": "raspberry_pi",
          "status": "online",
          "last_seen": "2023-08-15T10:30:45Z"
        },
        ...
      ]
    }
  }
  ```

#### 获取单个设备信息

- **URL**: `/api/devices/{device_id}`
- **方法**: `GET`
- **功能**: 获取特定设备的详细信息
- **响应**:
  ```json
  {
    "success": true,
    "data": {
      "device": {
        "id": "rpi-001",
        "name": "客厅树莓派",
        "type": "raspberry_pi",
        "status": "online",
        "ip_address": "192.168.1.100",
        "mac_address": "b8:27:eb:xx:xx:xx",
        "last_seen": "2023-08-15T10:30:45Z",
        "os_info": "Raspbian GNU/Linux 11 (bullseye)",
        "hardware_info": {...},
        "connected_sensors": [...],
        "connected_actuators": [...]
      }
    }
  }
  ```

#### 添加设备

- **URL**: `/api/devices`
- **方法**: `POST`
- **功能**: 添加一个新设备到系统
- **请求体**:
  ```json
  {
    "id": "rpi-003",
    "name": "厨房树莓派",
    "type": "raspberry_pi",
    "description": "厨房温度监控"
  }
  ```
- **响应**:
  ```json
  {
    "success": true,
    "data": {
      "device": {
        "id": "rpi-003",
        "name": "厨房树莓派",
        "type": "raspberry_pi",
        "status": "pending",
        "created_at": "2023-08-15T14:25:30Z"
      }
    },
    "message": "设备添加成功"
  }
  ```

#### 控制设备

- **URL**: `/api/devices/{device_id}/control`
- **方法**: `POST`
- **功能**: 向设备发送控制命令
- **请求体**:
  ```json
  {
    "command": "toggle",
    "target": "GPIO18",
    "params": {
      "state": "on"
    }
  }
  ```
- **响应**:
  ```json
  {
    "success": true,
    "data": {
      "command_id": "cmd-12345",
      "status": "sent",
      "timestamp": "2023-08-15T16:20:15Z"
    },
    "message": "命令已发送"
  }
  ```

### 系统监控接口

#### 获取API状态

- **URL**: `/api/status`
- **方法**: `GET`
- **功能**: 检查API服务是否正常运行
- **响应**:
  ```json
  {
    "success": true,
    "data": {
      "status": "running",
      "version": "1.0.0",
      "uptime": 3654,
      "server_time": "2023-08-15T17:30:45Z"
    }
  }
  ```

#### 获取系统监控数据

- **URL**: `/api/monitor`
- **方法**: `GET`
- **功能**: 获取系统性能监控数据
- **响应**:
  ```json
  {
    "success": true,
    "data": {
      "server": {
        "cpu_usage": 23.5,
        "memory_usage": 42.8,
        "disk_usage": 75.2,
        "network": {
          "rx_bytes": 1024576,
          "tx_bytes": 512288
        }
      },
      "devices": {
        "total": 5,
        "online": 3,
        "offline": 2
      },
      "mqtt": {...},
      "influxdb": {...}
    }
  }
  ```

### 自然语言处理接口

#### 发送自然语言命令

- **URL**: `/api/langchain/process`
- **方法**: `POST`
- **功能**: 向特定设备发送自然语言命令
- **请求体**:
  ```json
  {
    "device_id": "rpi-001",
    "query": "打开客厅的灯",
    "context": {
      "room": "客厅",
      "time": "evening"
    }
  }
  ```
- **响应**:
  ```json
  {
    "success": true,
    "data": {
      "response": "已将打开灯的命令发送到客厅树莓派",
      "command_executed": {
        "type": "device_control",
        "target": "GPIO18",
        "action": "set",
        "params": {
          "state": "on"
        }
      },
      "confidence": 0.92
    }
  }
  ``` 
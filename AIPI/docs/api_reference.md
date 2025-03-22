# AIPI系统API参考

本文档详细列出AIPI系统提供的所有API接口，包括请求方法、参数、响应格式和示例。

## API概览

AIPI系统API采用RESTful架构，所有端点均以`/api`开头，使用JSON格式进行数据交换。大多数API请求需要有效的JWT令牌进行认证。

## 基本URL

```
http://<服务器地址>:5000/api
```

## 认证

大多数API请求需要在HTTP头部中包含有效的JWT令牌，可以通过`/api/login`端点获取。

```
Authorization: Bearer <JWT令牌>
```

## 通用响应格式

### 成功响应

```json
{
  "success": true,
  "data": { ... },  // 响应数据
  "message": "操作成功"  // 可选的成功消息
}
```

### 错误响应

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",  // 错误代码
    "message": "错误描述"    // 错误消息
  }
}
```

## 认证API

### 登录

获取JWT令牌进行API认证。

- **URL**: `/api/login`
- **方法**: `POST`
- **认证**: 不需要

**请求体**:

```json
{
  "username": "admin",
  "password": "your_password"
}
```

**响应**:

```json
{
  "success": true,
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires": 3600  // 过期时间（秒）
  },
  "message": "登录成功"
}
```

### 登出

使当前JWT令牌失效。

- **URL**: `/api/logout`
- **方法**: `POST`
- **认证**: 需要

**响应**:

```json
{
  "success": true,
  "message": "登出成功"
}
```

## 设备管理API

### 获取设备列表

获取所有注册设备的列表。

- **URL**: `/api/devices`
- **方法**: `GET`
- **认证**: 需要

**响应**:

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
      {
        "id": "rpi-002",
        "name": "卧室树莓派",
        "type": "raspberry_pi",
        "status": "offline",
        "last_seen": "2023-08-14T22:15:30Z"
      }
    ]
  }
}
```

### 获取单个设备信息

获取特定设备的详细信息。

- **URL**: `/api/devices/{device_id}`
- **方法**: `GET`
- **认证**: 需要

**响应**:

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
      "hardware_info": {
        "model": "Raspberry Pi 4 Model B",
        "cpu_temp": 45.2,
        "memory_usage": 35.7,
        "cpu_usage": 12.5,
        "disk_usage": 68.3
      },
      "connected_sensors": [
        {
          "pin": "GPIO17",
          "type": "temperature",
          "name": "室温传感器"
        },
        {
          "pin": "GPIO27",
          "type": "humidity",
          "name": "湿度传感器"
        }
      ],
      "connected_actuators": [
        {
          "pin": "GPIO18",
          "type": "relay",
          "name": "灯光控制"
        }
      ]
    }
  }
}
```

### 添加设备

添加一个新设备到系统。

- **URL**: `/api/devices`
- **方法**: `POST`
- **认证**: 需要

**请求体**:

```json
{
  "id": "rpi-003",
  "name": "厨房树莓派",
  "type": "raspberry_pi",
  "description": "厨房温度监控"
}
```

**响应**:

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

### 更新设备

更新设备信息。

- **URL**: `/api/devices/{device_id}`
- **方法**: `PUT`
- **认证**: 需要

**请求体**:

```json
{
  "name": "新厨房树莓派",
  "description": "更新后的描述"
}
```

**响应**:

```json
{
  "success": true,
  "data": {
    "device": {
      "id": "rpi-003",
      "name": "新厨房树莓派",
      "description": "更新后的描述",
      "updated_at": "2023-08-15T15:10:22Z"
    }
  },
  "message": "设备更新成功"
}
```

### 删除设备

从系统中删除设备。

- **URL**: `/api/devices/{device_id}`
- **方法**: `DELETE`
- **认证**: 需要

**响应**:

```json
{
  "success": true,
  "message": "设备删除成功"
}
```

### 控制设备

向设备发送控制命令。

- **URL**: `/api/devices/{device_id}/control`
- **方法**: `POST`
- **认证**: 需要

**请求体**:

```json
{
  "command": "toggle",
  "target": "GPIO18",
  "params": {
    "state": "on"
  }
}
```

**响应**:

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

### 获取设备历史数据

获取设备的历史数据记录。

- **URL**: `/api/devices/{device_id}/history`
- **方法**: `GET`
- **认证**: 需要

**查询参数**:

- `start_time`: 开始时间（ISO 8601格式，如`2023-08-14T00:00:00Z`）
- `end_time`: 结束时间（ISO 8601格式）
- `metrics`: 要查询的指标（逗号分隔，如`temperature,humidity`）
- `interval`: 数据聚合间隔（如`5m`表示5分钟）
- `limit`: 返回结果数量限制（默认100）

**响应**:

```json
{
  "success": true,
  "data": {
    "device_id": "rpi-001",
    "metrics": ["temperature", "humidity"],
    "interval": "5m",
    "records": [
      {
        "timestamp": "2023-08-15T10:00:00Z",
        "temperature": 24.5,
        "humidity": 65.3
      },
      {
        "timestamp": "2023-08-15T10:05:00Z",
        "temperature": 24.7,
        "humidity": 64.8
      },
      // ...更多数据点
    ]
  }
}
```

## 系统监控API

### 获取API状态

检查API服务是否正常运行。

- **URL**: `/api/status`
- **方法**: `GET`
- **认证**: 不需要

**响应**:

```json
{
  "success": true,
  "data": {
    "status": "running",
    "version": "1.0.0",
    "uptime": 3654,  // 秒
    "server_time": "2023-08-15T17:30:45Z"
  }
}
```

### 获取系统监控数据

获取系统性能监控数据。

- **URL**: `/api/monitor`
- **方法**: `GET`
- **认证**: 需要

**响应**:

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
    "mqtt": {
      "status": "connected",
      "messages_received": 15264,
      "messages_sent": 8752
    },
    "influxdb": {
      "status": "connected",
      "writes": 12450,
      "queries": 320
    }
  }
}
```

## 自然语言处理API

### 发送自然语言命令

向特定设备发送自然语言命令。

- **URL**: `/api/langchain/process`
- **方法**: `POST`
- **认证**: 需要

**请求体**:

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

**响应**:

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

## 告警API

### 获取告警列表

获取系统中的告警信息。

- **URL**: `/api/alerts`
- **方法**: `GET`
- **认证**: 需要

**查询参数**:

- `status`: 告警状态（`active`, `acknowledged`, `resolved`, `all`，默认为`active`）
- `device_id`: 按设备ID筛选
- `severity`: 按严重程度筛选（`info`, `warning`, `critical`）
- `start_time`: 开始时间（ISO 8601格式）
- `limit`: 返回结果数量限制（默认50）

**响应**:

```json
{
  "success": true,
  "data": {
    "alerts": [
      {
        "id": "alert-001",
        "device_id": "rpi-001",
        "timestamp": "2023-08-15T16:45:30Z",
        "type": "high_temperature",
        "severity": "warning",
        "message": "客厅温度超过阈值：28.5°C",
        "status": "active",
        "value": 28.5,
        "threshold": 27.0
      },
      {
        "id": "alert-002",
        "device_id": "rpi-002",
        "timestamp": "2023-08-15T12:20:15Z",
        "type": "connection_lost",
        "severity": "critical",
        "message": "卧室树莓派连接中断",
        "status": "acknowledged",
        "acknowledged_by": "admin",
        "acknowledged_at": "2023-08-15T12:25:32Z"
      }
    ],
    "total": 2,
    "page": 1,
    "limit": 50
  }
}
```

### 确认告警

确认收到告警信息。

- **URL**: `/api/alerts/{alert_id}/acknowledge`
- **方法**: `POST`
- **认证**: 需要

**请求体**:

```json
{
  "notes": "已知晓，正在处理"
}
```

**响应**:

```json
{
  "success": true,
  "data": {
    "alert": {
      "id": "alert-001",
      "status": "acknowledged",
      "acknowledged_by": "admin",
      "acknowledged_at": "2023-08-15T17:05:22Z",
      "notes": "已知晓，正在处理"
    }
  },
  "message": "告警已确认"
}
```

## 错误代码及处理

| 错误代码 | 描述 | 建议解决方案 |
|---------|------|-------------|
| `AUTH_INVALID_CREDENTIALS` | 用户名或密码错误 | 检查用户名和密码是否正确 |
| `AUTH_TOKEN_EXPIRED` | JWT令牌已过期 | 重新登录获取新的令牌 |
| `AUTH_TOKEN_INVALID` | JWT令牌无效 | 确保令牌格式正确，或重新登录 |
| `AUTH_INSUFFICIENT_PERMISSIONS` | 权限不足 | 联系管理员获取适当的权限 |
| `DEVICE_NOT_FOUND` | 设备不存在 | 检查设备ID是否正确 |
| `DEVICE_OFFLINE` | 设备离线 | 等待设备重新连接，或检查设备网络 |
| `COMMAND_INVALID` | 命令格式错误 | 检查命令格式是否符合API要求 |
| `SERVER_ERROR` | 服务器内部错误 | 检查服务器日志或联系系统管理员 |
| `DB_ERROR` | 数据库错误 | 检查数据库连接或联系系统管理员 |
| `MQTT_ERROR` | MQTT连接错误 | 检查MQTT服务器状态或配置 |

## API使用示例

### JavaScript示例（使用fetch）

```javascript
// 登录示例
async function login(username, password) {
  const response = await fetch('http://your-server:5000/api/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ username, password })
  });
  
  const data = await response.json();
  if (data.success) {
    // 保存令牌用于后续请求
    localStorage.setItem('token', data.data.token);
    return data.data.token;
  } else {
    throw new Error(data.error.message);
  }
}

// 控制设备示例
async function controlDevice(deviceId, command, target, params) {
  const token = localStorage.getItem('token');
  if (!token) {
    throw new Error('未登录');
  }
  
  const response = await fetch(`http://your-server:5000/api/devices/${deviceId}/control`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({ command, target, params })
  });
  
  const data = await response.json();
  if (data.success) {
    return data.data;
  } else {
    throw new Error(data.error.message);
  }
}

// 使用示例
async function example() {
  try {
    await login('admin', 'password');
    const result = await controlDevice('rpi-001', 'toggle', 'GPIO18', { state: 'on' });
    console.log('命令发送成功:', result);
  } catch (error) {
    console.error('错误:', error.message);
  }
}
``` 
# AIPI文档中心

这是AIPI项目的文档中心，提供系统架构、安装指南和API参考。

## 文档目录

- [系统架构](system_architecture.md) - 详细的系统设计和组件交互
- [API参考](api_reference.md) - 完整的API接口文档
- [树莓派安装指南](raspberry_pi_installation.md) - 如何在树莓派上安装和配置AIPI客户端
- [MQTT服务器设置](mqtt_server_setup.md) - MQTT消息代理的安装和配置
- [LangChain集成](langchain_setup.md) - 设置和使用LangChain进行自然语言处理
- [使用指南](usage_guide.md) - 系统使用和操作指南

## 快速开始

### 服务器端

1. 克隆仓库:
   ```bash
   git clone https://github.com/yourusername/AIPI.git
   cd AIPI/server
   ```

2. 安装依赖:
   ```bash
   pip install -r requirements.txt
   ```

3. 配置环境:
   ```bash
   cp .env.example .env
   # 编辑.env文件，填写必要的配置参数
   ```

4. 启动服务:
   ```bash
   python run.py
   ```

### 树莓派客户端

1. 克隆仓库:
   ```bash
   git clone https://github.com/yourusername/AIPI.git
   cd AIPI/raspberry_pi
   ```

2. 安装依赖:
   ```bash
   pip install -r requirements.txt
   ```

3. 配置环境:
   ```bash
   cp .env.example .env
   # 编辑.env文件，填写必要的配置参数
   ```

4. 启动客户端:
   ```bash
   python rpi_run.py
   ```

## 独立运行API服务器

如果只需要API服务，可以单独运行API服务器：

```bash
cd AIPI/server
python api-web.py
```

API服务器提供以下主要端点：

- `/api/status` - 获取API状态
- `/api/login` - 用户认证
- `/api/devices` - 获取设备列表
- `/api/devices/{id}` - 获取特定设备信息
- `/api/devices/{id}/control` - 控制设备
- `/api/devices/{id}/history` - 获取设备历史数据
- `/api/monitor` - 获取系统监控数据

详细API文档请参考 [API参考](api_reference.md)。

## 其他资源

- [更新日志](CHANGELOG.md)
- [贡献指南](CONTRIBUTING.md)
- [常见问题](FAQ.md) 
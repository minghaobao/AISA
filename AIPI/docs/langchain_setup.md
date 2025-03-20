# LangChain配置与本地服务启动指南

本文档详细说明AI命令执行系统中LangChain的配置方法，以及如何启动完整的本地服务。

## LangChain简介

LangChain是一个强大的框架，用于开发由大型语言模型（LLM）驱动的应用程序。在我们的系统中，LangChain用于：
1. 将自然语言请求转换为具体的Linux命令
2. 管理与设备的交互和上下文记忆
3. 提供工具抽象层，支持命令执行和状态查询

## OpenAI API配置

### 获取API密钥

首先，您需要获取OpenAI API密钥：

1. 访问[OpenAI官网](https://openai.com/api/)并创建账户
2. 导航至API密钥页面
3. 创建新的API密钥
4. 保存密钥，我们将在环境配置中使用它

### 环境变量配置

系统通过环境变量管理OpenAI API密钥和其他配置：

1. 复制示例环境文件：
   ```bash
   cp ai_mqtt_langchain/.env.example ai_mqtt_langchain/.env
   ```

2. 编辑`.env`文件，填入您的API密钥和其他参数：
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   OPENAI_MODEL_NAME=gpt-3.5-turbo  # 或 gpt-4，取决于您的需求和访问权限
   
   # MQTT配置
   MQTT_HOST=localhost
   MQTT_PORT=1883
   MQTT_USERNAME=mqtt_user  # 如果配置了认证
   MQTT_PASSWORD=mqtt_password  # 如果配置了认证
   
   # 设备配置
   DEVICE_IDS=rpi_001,rpi_002  # 逗号分隔的设备ID列表
   ```

## LangChain命令代理配置

### 模型选择

系统默认使用`gpt-3.5-turbo`，但您可以根据需要更改为其他模型：

```
OPENAI_MODEL_NAME=gpt-4-turbo-preview  # 更高性能，但成本更高
```

或者在命令行中指定：

```bash
python ai_mqtt_langchain/langchain_command_agent.py --device-id rpi_001 --model gpt-4
```

### 温度设置

温度控制响应的随机性，默认为0（最确定性）：

```python
# 在langchain_command_agent.py中
self.llm = ChatOpenAI(
    openai_api_key=openai_api_key,
    temperature=0,  # 0-1之间，值越高结果越随机
    model_name=model_name
)
```

### 内存配置

对话历史记忆默认使用`ConversationBufferMemory`，可以根据需要修改：

```python
# 默认内存配置
self.memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

# 可选：使用有限历史记忆（仅保留最近k轮对话）
# from langchain.memory import ConversationBufferWindowMemory
# self.memory = ConversationBufferWindowMemory(memory_key="chat_history", k=5, return_messages=True)
```

## 扩展LangChain工具

您可以通过添加新工具来扩展系统功能：

1. 在`langchain_command_agent.py`中的`add_device`方法内添加新工具：

```python
# 示例：添加一个专用于GPIO控制的工具
gpio_control_tool = Tool(
    name=f"control_gpio_on_{device_id}",
    func=lambda pin_cmd: self.gpio_controller.execute(device_id, pin_cmd),
    description=f"控制设备 {device_id} 上的GPIO引脚。格式：'引脚号 状态'，例如 '18 HIGH'"
)
self.tools.append(gpio_control_tool)
```

2. 实现相应的功能处理逻辑
3. 更新代理：`self._create_agent()`

## 本地服务启动流程

完整系统包括多个组件，需要按特定顺序启动：

### 1. 启动MQTT服务器

这是所有通信的基础：

```bash
# Linux
sudo systemctl start mosquitto

# Windows
net start mosquitto

# Docker
cd mqtt-server
docker-compose up -d
```

确认MQTT服务器正常运行：

```bash
# 测试订阅
mosquitto_sub -h localhost -t "test/topic" -v
```

### 2. 启动设备命令执行器

在每个设备（如树莓派）上：

```bash
# 直接启动
python ai_mqtt_langchain/rpi_command_executor.py

# 或使用系统服务（如已配置）
sudo systemctl start rpi-command-executor.service
```

验证设备已连接：

```bash
# 订阅设备状态主题
mosquitto_sub -h localhost -t "device/+/status" -v
```

几秒钟后，您应该能看到设备发送的心跳消息。

### 3. 启动LangChain命令代理

最后，启动AI命令代理：

```bash
python ai_mqtt_langchain/langchain_command_agent.py --device-id rpi_001
```

如果需要支持多设备，可以启动多个实例，每个针对不同设备。

## 完整启动脚本

为了简化启动过程，您可以创建一个启动脚本：

```bash
#!/bin/bash
# 文件名: start_system.sh

# 检查MQTT服务器
echo "检查MQTT服务器..."
if ! pgrep mosquitto > /dev/null; then
    echo "启动MQTT服务器..."
    sudo systemctl start mosquitto
fi

# 等待MQTT服务器完全启动
sleep 2

# 启动AI命令代理
echo "启动AI命令代理..."
cd /path/to/your/project
python ai_mqtt_langchain/langchain_command_agent.py --device-id rpi_001
```

使脚本可执行并运行：

```bash
chmod +x start_system.sh
./start_system.sh
```

## 配置代理行为

### 代理类型

系统使用`CHAT_CONVERSATIONAL_REACT_DESCRIPTION`代理类型，这是一个会话式代理，适合多轮对话：

```python
self.agent = initialize_agent(
    tools=self.tools,
    llm=self.llm,
    agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
    verbose=True,
    memory=self.memory,
    handle_parsing_errors=True,
    callbacks=self.callbacks
)
```

如需更改代理类型，可修改`_create_agent`方法中的`agent`参数。

### 提示模板定制

如需自定义代理的提示模板，可以添加以下代码：

```python
from langchain.prompts import PromptTemplate

# 定义自定义提示模板
custom_template = """作为AI命令助手，您的任务是帮助用户与设备 {device_id} 交互。
分析用户的自然语言请求，并将其转换为适当的Linux命令。
您可以使用以下工具：
{tools}

历史对话：
{chat_history}

用户请求：{input}
"""

# 创建提示模板
prompt = PromptTemplate(
    input_variables=["device_id", "tools", "chat_history", "input"],
    template=custom_template
)

# 在初始化代理时使用
self.agent = initialize_agent(
    # ...其他参数...
    agent_kwargs={"prompt": prompt}
)
```

## 多设备并行管理

如果您需要同时管理多个设备，可以使用以下方法：

### 1. 配置多设备

在`.env`文件中列出所有设备：

```
DEVICE_IDS=rpi_001,rpi_002,rpi_003
```

### 2. 批量启动设备监控

创建一个脚本自动为所有设备启动代理：

```python
# 文件名: start_all_agents.py
import os
import subprocess
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 获取设备列表
devices = os.getenv("DEVICE_IDS", "").split(",")

# 为每个设备启动一个代理进程
processes = []
for device in devices:
    if device.strip():
        cmd = ["python", "ai_mqtt_langchain/langchain_command_agent.py", "--device-id", device.strip()]
        process = subprocess.Popen(cmd)
        processes.append((device, process))
        print(f"已为设备 {device} 启动代理，PID: {process.pid}")

# 等待所有进程完成
try:
    for device, process in processes:
        process.wait()
except KeyboardInterrupt:
    print("正在停止所有代理...")
    for device, process in processes:
        process.terminate()
```

运行此脚本：

```bash
python start_all_agents.py
```

## 故障排除

### LangChain API错误

**问题**: `AuthenticationError: Incorrect API key provided`

**解决方案**:
1. 检查`.env`文件中的API密钥是否正确
2. 确认环境变量已正确加载：
   ```python
   import os
   print(os.getenv("OPENAI_API_KEY"))
   ```

### 响应超时

**问题**: 代理响应非常慢或超时

**解决方案**:
1. 检查网络连接
2. 考虑使用更轻量级的模型
3. 增加超时设置：
   ```python
   self.llm = ChatOpenAI(
       # ...其他参数...
       request_timeout=60  # 秒
   )
   ```

### 内存使用过高

**问题**: 长时间运行后内存占用过高

**解决方案**:
1. 使用WindowMemory限制历史记忆量
2. 定期重启服务
3. 优化提示模板，减少不必要的内容

## 高级LangChain配置

### 使用自定义回调

系统已实现`CommandAgentCallbacks`类用于跟踪代理行为。您可以扩展它记录更多信息：

```python
class CustomCallbacks(CommandAgentCallbacks):
    def on_llm_start(self, serialized, prompts, **kwargs):
        super().on_llm_start(serialized, prompts, **kwargs)
        # 记录完整提示到文件
        with open("prompts_log.txt", "a") as f:
            f.write(f"--- 新提示 {datetime.now().isoformat()} ---\n")
            for prompt in prompts:
                f.write(f"{prompt}\n")
            f.write("---\n")
```

### 集成向量数据库

如需增加系统对命令的理解，可以集成向量数据库：

```python
from langchain.vectorstores import Chroma
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.docstore.document import Document

# 创建命令知识库
docs = [
    Document(page_content="ls - 列出目录内容", metadata={"category": "file"}),
    Document(page_content="ps - 报告当前进程状态", metadata={"category": "process"}),
    # 更多命令...
]

# 创建向量数据库
embeddings = OpenAIEmbeddings()
vectordb = Chroma.from_documents(docs, embeddings)

# 创建检索工具
retriever = vectordb.as_retriever()
command_lookup_tool = Tool(
    name="command_lookup",
    func=lambda q: retriever.get_relevant_documents(q),
    description="查找Linux命令的用法和示例"
)
```

## 完整服务架构图

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  LangChain代理  │◄────►   MQTT服务器    │◄────►  设备命令执行器  │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
       ▲                                               │
       │                                               │
       │                                               ▼
┌─────────────────┐                           ┌─────────────────┐
│                 │                           │                 │
│  用户交互界面   │                           │  设备系统命令   │
│                 │                           │                 │
└─────────────────┘                           └─────────────────┘
```

## 进一步阅读

- [LangChain官方文档](https://python.langchain.com/docs/get_started/introduction)
- [OpenAI API文档](https://platform.openai.com/docs/api-reference)
- [Mosquitto MQTT文档](https://mosquitto.org/documentation/) 
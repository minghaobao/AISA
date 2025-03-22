# LangChain集成指南

本指南详细说明如何在AIPI系统中设置和配置LangChain组件，用于自然语言处理和命令解析。

## 1. LangChain简介

LangChain是一个强大的框架，用于开发由大型语言模型(LLM)驱动的应用程序。在AIPI系统中，LangChain负责：

- 解析自然语言命令
- 将命令转换为具体的设备控制指令
- 生成响应并解释执行结果
- 支持多轮对话和上下文管理

## 2. 环境准备

### 2.1 安装依赖

LangChain依赖已包含在`requirements.txt`文件中，主要包括：

```
langchain>=0.1.0
langchain-core>=0.1.0
langchain-openai>=0.1.0
openai>=1.0.0
```

安装依赖：
```bash
pip install -r requirements.txt
```

### 2.2 API密钥配置

对于OpenAI模型，您需要在`.env`文件中设置API密钥：

```
# OpenAI API配置
OPENAI_API_KEY=your_api_key_here
LLM_MODEL=gpt-3.5-turbo  # 可选: gpt-4, gpt-4-1106-preview
LLM_TEMPERATURE=0.1
```

如果您希望使用其他LLM提供商，可以配置相应的API密钥，例如：

```
# Anthropic API配置
ANTHROPIC_API_KEY=your_anthropic_key_here

# Hugging Face API配置
HUGGINGFACE_API_KEY=your_huggingface_key_here
```

## 3. 系统组件

AIPI系统中的LangChain集成包含以下主要组件：

### 3.1 服务器端LangChain处理器

位置：`server/langchain_processor.py`

功能：
- 接收来自Web界面的自然语言命令
- 处理命令并生成设备控制指令
- 通过MQTT发送指令到相应设备
- 接收并处理设备响应

### 3.2 树莓派端LangChain处理器

位置：`raspberry_pi/langchain_processor.py`

功能：
- 接收特定于设备的自然语言命令
- 在本地处理命令，无需服务器参与
- 执行GPIO控制、传感器读取等本地任务
- 返回执行结果

## 4. 配置LangChain

### 4.1 基本配置

在服务器和树莓派上，LangChain处理器配置相似。主要配置包括：

**模型选择**：
```python
# 在config.py中
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))
```

**对话历史记录**：
```python
# 在langchain_processor.py中
CONVERSATION_HISTORY_LENGTH = int(os.getenv("CONVERSATION_HISTORY_LENGTH", "10"))
```

### 4.2 工具和函数定义

LangChain处理器使用自定义工具来执行特定任务。以下是一些预定义的工具示例：

**设备控制工具**：
```python
@tool
def control_device(pin: str, action: str, parameters: Optional[Dict] = None) -> str:
    """控制设备的GPIO引脚。
    
    Args:
        pin: 要控制的引脚名称，例如'relay_1','fan_1'
        action: 动作，如'on','off','toggle','speed'
        parameters: 其他参数，如设置风扇速度时的'speed'值
        
    Returns:
        操作结果描述
    """
    # 控制逻辑实现
    ...
```

**传感器读取工具**：
```python
@tool
def read_sensor(sensor_type: str) -> str:
    """读取传感器数据。
    
    Args:
        sensor_type: 传感器类型，如'temperature','humidity'
        
    Returns:
        传感器读数
    """
    # 读取传感器逻辑实现
    ...
```

## 5. 自定义LangChain提示

### 5.1 系统提示模板

AIPI系统使用自定义提示模板来指导LLM的行为。以下是树莓派处理器使用的基本系统提示：

```python
SYSTEM_PROMPT = """你是一个智能家居助手，负责控制树莓派设备。

你可以控制的设备包括：
1. 继电器 (relay_1, relay_2): 可以打开(on)、关闭(off)或切换状态(toggle)
2. 风扇 (fan_1): 可以打开、关闭，或设置速度(speed)，速度范围0-100
3. 灯光 (light_1): 可以打开、关闭

你可以读取的传感器包括：
1. 温度传感器 (temperature): 返回当前温度
2. 湿度传感器 (humidity): 返回当前湿度
3. 系统状态 (system): 返回CPU、内存使用情况等

请使用提供的工具执行用户请求，并返回操作结果。
"""
```

### 5.2 自定义提示

您可以修改`langchain_processor.py`中的提示，以添加或更改可用的命令和描述：

```python
# 在config.py或.env中定义自定义提示
DEVICE_TYPE = os.getenv("DEVICE_TYPE", "智能家居控制设备")
DEVICE_CAPABILITIES = os.getenv("DEVICE_CAPABILITIES", """
- 控制继电器(relay_1-relay_4)
- 调节风扇速度(fan_1-fan_2)
- 控制LED灯(led_1-led_3)
- 读取温湿度传感器
- 监控系统状态
""")

# 在langchain_processor.py中使用这些变量
SYSTEM_PROMPT = f"""你是一个{DEVICE_TYPE}的智能助手。

你可以执行以下操作：
{DEVICE_CAPABILITIES}

请使用提供的工具执行用户请求，并返回操作结果。
"""
```

## 6. 扩展LangChain功能

### 6.1 添加新工具

要添加新的设备控制能力，您需要：

1. 在`langchain_processor.py`中定义新的工具函数：

```python
@tool
def control_new_device(device_id: str, action: str) -> str:
    """控制新添加的设备。
    
    Args:
        device_id: 设备标识符
        action: 要执行的动作
        
    Returns:
        操作结果
    """
    # 实现控制逻辑
    ...
    return f"成功控制{device_id}执行{action}操作"
```

2. 更新系统提示以包含新设备：

```python
SYSTEM_PROMPT = """你是一个智能家居助手，负责控制树莓派设备。

你可以控制的设备包括：
...
4. 新设备 (new_device): 可以执行特定操作

请使用提供的工具执行用户请求。
"""
```

### 6.2 实现自定义Agent

对于更复杂的场景，您可以实现自定义Agent：

```python
from langchain.agents import initialize_agent, AgentType

# 创建自定义Agent
def create_custom_agent(llm, tools):
    agent = initialize_agent(
        tools, 
        llm, 
        agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=5
    )
    return agent
```

## 7. 多语言支持

AIPI系统支持多语言自然语言处理。要启用不同语言的支持：

1. 在系统提示中指定语言偏好：

```python
SYSTEM_PROMPT = """你是一个智能家居助手，负责控制树莓派设备。
用户可能用中文或英文与你交流，请使用用户使用的语言回复。

你可以控制的设备包括：
...
"""
```

2. 确保您使用的LLM模型支持目标语言（如GPT-3.5/4已支持多种语言）

## 8. 测试与调试

### 8.1 测试LangChain处理器

您可以使用以下命令测试LangChain处理器：

```bash
# 在服务器端
cd AIPI/server
python test_langchain.py --query "打开客厅的灯"

# 在树莓派端
cd AIPI/raspberry_pi
python test_langchain.py --query "打开继电器1"
```

### 8.2 调试提示

如果LangChain处理器无法正确理解命令，您可以：

1. 启用详细日志：
```python
import langchain
langchain.verbose = True
```

2. 查看完整的提示和响应：
```python
# 在langchain_processor.py中
print(f"System Prompt: {SYSTEM_PROMPT}")
print(f"User Query: {query}")
print(f"LLM Response: {response}")
```

3. 调整提示模板和示例以提高理解能力

## 9. 高级功能

### 9.1 记忆功能

LangChain处理器支持对话记忆，使其能够记住上下文：

```python
from langchain.memory import ConversationBufferWindowMemory

# 创建对话记忆
memory = ConversationBufferWindowMemory(
    k=CONVERSATION_HISTORY_LENGTH,
    return_messages=True,
    memory_key="chat_history",
    output_key="output"
)
```

### 9.2 结构化输出

要确保LLM生成结构化响应，可以使用OutputParser：

```python
from langchain.output_parsers import ResponseSchema, StructuredOutputParser

# 定义响应结构
response_schemas = [
    ResponseSchema(name="action", description="执行的操作"),
    ResponseSchema(name="status", description="操作的状态，成功或失败"),
    ResponseSchema(name="message", description="操作结果的详细描述")
]

# 创建输出解析器
output_parser = StructuredOutputParser.from_response_schemas(response_schemas)
```

### 9.3 异步处理

对于高负载场景，可以使用异步处理：

```python
import asyncio
from langchain.llms import OpenAI

async def process_command_async(query, device_id):
    # 异步处理逻辑
    ...
    return response
```

## 10. 故障排除

### 10.1 LLM模型错误

如果遇到LLM API错误：
- 检查API密钥是否正确
- 验证网络连接
- 查看API限流和配额状态
- 尝试使用不同的模型

### 10.2 解析错误

如果LangChain无法正确解析命令：
- 检查提示模板是否清晰
- 增加示例数量
- 降低温度设置以减少随机性
- 使用更高级的模型（如gpt-4）

### 10.3 工具执行错误

如果工具执行失败：
- 检查工具函数是否有错误
- 验证参数类型和范围
- 查看设备控制器日志
- 确保GPIO权限正确

## 11. 参考资源

- [LangChain官方文档](https://python.langchain.com/docs/get_started/introduction)
- [OpenAI API文档](https://platform.openai.com/docs/api-reference)
- [树莓派GPIO编程指南](https://www.raspberrypi.org/documentation/usage/gpio/)
- [MQTT消息格式文档](mqtt_server_setup.md) 
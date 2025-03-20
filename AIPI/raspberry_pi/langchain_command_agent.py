#!/usr/bin/env python3
import os
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

from langchain.agents import Tool
from langchain.agents import initialize_agent
from langchain.agents import AgentType
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import AgentAction, AgentFinish, LLMResult

import paho.mqtt.client as mqtt

class MQTTCommandExecutor:
    """MQTT命令执行器，负责发送命令到设备并获取结果"""
    
    def __init__(self, 
                 mqtt_host: str, 
                 mqtt_port: int = 1883, 
                 mqtt_username: Optional[str] = None, 
                 mqtt_password: Optional[str] = None,
                 default_timeout: int = 60,
                 default_wait_time: int = 30):
        """初始化MQTT命令执行器"""
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.mqtt_username = mqtt_username
        self.mqtt_password = mqtt_password
        self.default_timeout = default_timeout
        self.default_wait_time = default_wait_time
        
        # 设备命令结果
        self.command_results = {}
        self.waiting_commands = set()
        
        # 设备状态
        self.device_status = {}
        
        # 创建MQTT客户端
        self.client_id = f"langchain_agent_{int(time.time())}"
        self.client = mqtt.Client(client_id=self.client_id)
        
        # 设置回调函数
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        
        # 设置认证信息
        if mqtt_username and mqtt_password:
            self.client.username_pw_set(mqtt_username, mqtt_password)
        
        # 连接标志
        self.connected = False
        
    def connect(self):
        """连接到MQTT代理服务器"""
        self.client.connect(self.mqtt_host, self.mqtt_port, keepalive=60)
        self.client.loop_start()
        
        # 等待连接建立
        start_time = time.time()
        while not self.connected and time.time() - start_time < 5:
            time.sleep(0.1)
            
        if not self.connected:
            raise ConnectionError("无法连接到MQTT代理服务器")
        
        return self.connected
    
    def disconnect(self):
        """断开与MQTT代理服务器的连接"""
        self.client.loop_stop()
        self.client.disconnect()
        self.connected = False
    
    def _on_connect(self, client, userdata, flags, rc):
        """MQTT连接回调函数"""
        if rc == 0:
            self.connected = True
            print(f"已连接到MQTT代理服务器 {self.mqtt_host}:{self.mqtt_port}")
        else:
            print(f"连接MQTT代理服务器失败，返回码: {rc}")
    
    def _on_message(self, client, userdata, msg):
        """MQTT消息回调函数"""
        topic = msg.topic
        try:
            payload = json.loads(msg.payload.decode('utf-8'))
            
            # 处理命令结果
            if "/result" in topic:
                device_id = topic.split("/")[1]
                command_id = payload.get("command_id")
                
                if command_id and command_id in self.waiting_commands:
                    self.command_results[command_id] = payload
                    self.waiting_commands.remove(command_id)
                    
            # 处理设备状态
            elif "/status" in topic:
                device_id = topic.split("/")[1]
                self.device_status[device_id] = payload
                
        except Exception as e:
            print(f"处理MQTT消息出错: {e}")
    
    def subscribe_to_device(self, device_id: str):
        """订阅设备的结果和状态主题"""
        if not self.connected:
            raise ConnectionError("MQTT客户端未连接")
            
        # 订阅设备结果主题
        result_topic = f"device/{device_id}/result"
        self.client.subscribe(result_topic)
        print(f"已订阅设备结果主题: {result_topic}")
        
        # 订阅设备状态主题
        status_topic = f"device/{device_id}/status"
        self.client.subscribe(status_topic)
        print(f"已订阅设备状态主题: {status_topic}")
    
    def execute_command(self, device_id: str, command: str, 
                         timeout: Optional[int] = None,
                         wait_time: Optional[int] = None) -> Dict[str, Any]:
        """执行命令并等待结果"""
        import uuid
        
        # 使用默认值
        timeout = timeout or self.default_timeout
        wait_time = wait_time or self.default_wait_time
        
        # 生成命令ID
        command_id = str(uuid.uuid4())
        
        # 准备命令数据
        command_data = {
            "command_id": command_id,
            "command": command,
            "timeout": timeout
        }
        
        # 添加到等待命令集合
        self.waiting_commands.add(command_id)
        
        # 发送命令
        command_topic = f"device/{device_id}/command"
        self.client.publish(command_topic, json.dumps(command_data))
        print(f"已发送命令到设备 {device_id}: {command}")
        
        # 等待结果
        start_time = time.time()
        while time.time() - start_time < wait_time and command_id in self.waiting_commands:
            time.sleep(0.1)
        
        # 获取结果
        result = self.command_results.get(command_id)
        
        if not result:
            return {
                "success": False,
                "error": f"等待命令结果超时（等待了{wait_time}秒）",
                "device_id": device_id,
                "command_id": command_id,
                "command": command,
                "timestamp": datetime.now().isoformat()
            }
        
        return result
        
    def get_device_status(self, device_id: str) -> Dict[str, Any]:
        """获取设备的最新状态"""
        return self.device_status.get(device_id, {"status": "unknown"})

class CommandAgentCallbacks(BaseCallbackHandler):
    """用于监控LangChain代理行为的回调处理器"""
    
    def on_llm_start(self, serialized, prompts, **kwargs):
        print("\n🤖 AI开始思考...")
        
    def on_llm_end(self, response, **kwargs):
        print("🤖 AI思考完成")
        
    def on_tool_start(self, serialized, input_str, **kwargs):
        print(f"\n🔧 开始使用工具: {serialized.get('name')}")
        print(f"输入: {input_str}")
        
    def on_tool_end(self, output, **kwargs):
        print(f"输出: {output}")
        print("🔧 工具使用完成")
        
    def on_agent_action(self, action, **kwargs):
        print(f"\n🚀 代理决定执行: {action.tool}")
        print(f"使用输入: {action.tool_input}")
        
    def on_agent_finish(self, finish, **kwargs):
        print(f"\n✅ 代理任务完成: {finish.return_values.get('output')}")

class LangChainCommandAgent:
    """使用LangChain和OpenAI创建智能命令代理"""
    
    def __init__(self, 
                 openai_api_key: str,
                 mqtt_host: str,
                 mqtt_port: int = 1883,
                 mqtt_username: Optional[str] = None,
                 mqtt_password: Optional[str] = None,
                 model_name: str = "gpt-3.5-turbo"):
        """初始化LangChain命令代理"""
        # 保存OpenAI API密钥
        self.openai_api_key = openai_api_key
        
        # 创建MQTT命令执行器
        self.command_executor = MQTTCommandExecutor(
            mqtt_host=mqtt_host,
            mqtt_port=mqtt_port,
            mqtt_username=mqtt_username,
            mqtt_password=mqtt_password
        )
        
        # 连接到MQTT代理服务器
        self.command_executor.connect()
        
        # 创建LLM
        self.llm = ChatOpenAI(
            openai_api_key=openai_api_key,
            temperature=0,
            model_name=model_name
        )
        
        # 创建内存
        self.memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        
        # 创建回调
        self.callbacks = [CommandAgentCallbacks()]
        
        # 创建工具
        self.tools = []
        
        # 创建代理
        self.agent = None
    
    def add_device(self, device_id: str):
        """添加设备并为其创建工具"""
        # 订阅设备主题
        self.command_executor.subscribe_to_device(device_id)
        
        # 创建执行命令的工具
        execute_command_tool = Tool(
            name=f"execute_command_on_{device_id}",
            func=lambda command: self.command_executor.execute_command(device_id, command),
            description=f"在设备 {device_id} 上执行Linux命令。提供完整的命令字符串作为参数。"
        )
        
        # 创建获取设备状态的工具
        get_status_tool = Tool(
            name=f"get_status_of_{device_id}",
            func=lambda _: self.command_executor.get_device_status(device_id),
            description=f"获取设备 {device_id} 的当前状态。不需要参数，只需输入空字符串。"
        )
        
        # 添加工具
        self.tools.extend([execute_command_tool, get_status_tool])
        
        # 更新代理
        self._create_agent()
        
        return self
    
    def _create_agent(self):
        """创建或更新代理"""
        if not self.tools:
            raise ValueError("没有可用的工具，请先添加设备")
            
        # 创建代理
        self.agent = initialize_agent(
            tools=self.tools,
            llm=self.llm,
            agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
            verbose=True,
            memory=self.memory,
            handle_parsing_errors=True,
            callbacks=self.callbacks
        )
        
        return self.agent
    
    def run(self, query: str) -> str:
        """运行代理"""
        if not self.agent:
            raise ValueError("代理未初始化，请先添加设备")
            
        result = self.agent.run(input=query)
        return result
    
    def close(self):
        """关闭代理和MQTT连接"""
        self.command_executor.disconnect()

def load_from_env():
    """从环境变量加载配置创建代理"""
    from dotenv import load_dotenv
    load_dotenv()
    
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError("未找到OPENAI_API_KEY环境变量")
        
    mqtt_host = os.getenv("MQTT_HOST", "localhost")
    mqtt_port = int(os.getenv("MQTT_PORT", "1883"))
    mqtt_username = os.getenv("MQTT_USERNAME")
    mqtt_password = os.getenv("MQTT_PASSWORD")
    model_name = os.getenv("OPENAI_MODEL_NAME", "gpt-3.5-turbo")
    
    agent = LangChainCommandAgent(
        openai_api_key=openai_api_key,
        mqtt_host=mqtt_host,
        mqtt_port=mqtt_port,
        mqtt_username=mqtt_username,
        mqtt_password=mqtt_password,
        model_name=model_name
    )
    
    # 添加设备
    devices = os.getenv("DEVICE_IDS", "").split(",")
    for device_id in devices:
        if device_id.strip():
            agent.add_device(device_id.strip())
    
    return agent

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="LangChain命令代理")
    parser.add_argument("--device-id", required=True, help="设备ID")
    parser.add_argument("--openai-api-key", help="OpenAI API密钥")
    parser.add_argument("--mqtt-host", default="localhost", help="MQTT代理服务器主机")
    parser.add_argument("--mqtt-port", type=int, default=1883, help="MQTT代理服务器端口")
    parser.add_argument("--mqtt-username", help="MQTT用户名")
    parser.add_argument("--mqtt-password", help="MQTT密码")
    parser.add_argument("--model", default="gpt-3.5-turbo", help="OpenAI模型名称")
    
    args = parser.parse_args()
    
    # 如果未提供命令行参数，尝试从环境变量加载
    if not args.openai_api_key:
        from dotenv import load_dotenv
        load_dotenv()
        args.openai_api_key = os.getenv("OPENAI_API_KEY")
        
    if not args.openai_api_key:
        print("错误: 未提供OpenAI API密钥")
        exit(1)
    
    # 创建代理
    agent = LangChainCommandAgent(
        openai_api_key=args.openai_api_key,
        mqtt_host=args.mqtt_host,
        mqtt_port=args.mqtt_port,
        mqtt_username=args.mqtt_username,
        mqtt_password=args.mqtt_password,
        model_name=args.model
    )
    
    # 添加设备
    agent.add_device(args.device_id)
    
    print(f"LangChain命令代理已准备就绪，可以向设备 {args.device_id} 发送命令")
    print("输入'exit'或'quit'退出")
    
    # 交互式命令循环
    try:
        while True:
            query = input("\n请输入您的问题或命令: ")
            
            if query.lower() in ["exit", "quit"]:
                break
                
            if query.strip():
                result = agent.run(query)
                print(f"\n结果: {result}")
    
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    finally:
        agent.close()
        print("已关闭连接，程序退出") 
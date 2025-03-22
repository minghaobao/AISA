import logging
import time
import json
from langchain.prompts.chat import ChatPromptTemplate
from langchain.chains import LLMChain
from langchain.llms import OpenAI
from config import LLM_CONFIG, LOG_CONFIG, DEVICE_RULES
import threading

# 配置日志
logging.basicConfig(
    level=LOG_CONFIG["level"],
    format=LOG_CONFIG["format"],
    filename=LOG_CONFIG.get("filename")
)
logger = logging.getLogger("langchain_processor")

# 全局变量，用于存储LLM和分析链
llm = None
analysis_chain = None

# 设备状态分析提示模板
DEVICE_ANALYSIS_TEMPLATE = """
你是一个智能设备监控和控制系统的AI分析师。
请分析以下设备数据，判断设备状态，并给出相应的控制指令。

设备数据:
设备ID: {device_id}
温度: {temperature}°C
湿度: {humidity}%
其他数据: {additional_data}
时间戳: {timestamp}

参考规则:
1. 如果温度超过{temp_high}°C，需要开启降温设备
2. 如果温度低于{temp_low}°C，需要开启加热设备
3. 如果湿度超过{humidity_high}%，需要开启除湿设备
4. 如果湿度低于{humidity_low}%，需要开启加湿设备
5. {additional_rules}

请分析当前设备状态，并给出以下JSON格式的响应:
{{
  "analysis": "对设备状态的分析",
  "device_status": "正常/警告/危险",
  "recommendations": ["建议1", "建议2"],
  "control_actions": [
    {{
      "device_id": "需要控制的设备ID",
      "action": "控制动作(on/off/adjust)",
      "parameters": {{
        "param1": "值1",
        "param2": "值2"
      }}
    }}
  ]
}}
"""

def init_llm():
    """初始化LLM"""
    global llm, analysis_chain
    
    try:
        # 检查API密钥
        if not LLM_CONFIG.get("api_key"):
            logger.error("未配置OpenAI API密钥，LLM初始化失败")
            return False
            
        # 初始化LLM
        llm = OpenAI(
            temperature=LLM_CONFIG.get("temperature", 0.1),
            openai_api_key=LLM_CONFIG.get("api_key"),
            model_name=LLM_CONFIG.get("model_name", "gpt-3.5-turbo")
        )
        
        # 创建分析提示模板
        device_analysis_prompt = ChatPromptTemplate.from_template(DEVICE_ANALYSIS_TEMPLATE)
        
        # 创建分析链
        analysis_chain = LLMChain(
            llm=llm,
            prompt=device_analysis_prompt,
            verbose=LLM_CONFIG.get("verbose", False)
        )
        
        logger.info(f"LLM初始化成功，使用模型: {LLM_CONFIG.get('model_name')}")
        return True
        
    except Exception as e:
        logger.error(f"LLM初始化失败: {str(e)}")
        return False

def init_processor():
    """
    初始化并启动LangChain处理器
    :return: None
    """
    try:
        logger.info("初始化LangChain处理器...")
        
        # 初始化LLM组件
        if not init_llm():
            logger.error("LLM组件初始化失败，LangChain处理器无法启动")
            return False
            
        # 设置MQTT监听
        setup_mqtt_listener()
        
        logger.info("LangChain处理器已启动，等待数据处理")
        
        # 保持处理器运行
        while True:
            time.sleep(10)  # 每10秒检查一次
            
    except Exception as e:
        logger.error(f"LangChain处理器初始化失败: {str(e)}")
        return False

def setup_mqtt_listener():
    """设置MQTT监听器，用于接收需要处理的数据"""
    try:
        # 导入MQTT客户端
        from mqtt_client import get_mqtt_client
        
        mqtt_client = get_mqtt_client()
        logger.info("LangChain处理器已连接到MQTT客户端")
        
        # MQTT客户端会调用process_device_data处理数据
        return True
        
    except Exception as e:
        logger.error(f"设置MQTT监听器失败: {str(e)}")
        return False

def process_device_data(topic, data):
    """
    处理设备数据
    :param topic: MQTT主题
    :param data: 设备数据字典
    :return: 处理结果
    """
    if not analysis_chain:
        logger.error("LangChain分析链未初始化，无法处理设备数据")
        return {"error": "LangChain未初始化"}
        
    try:
        device_id = data.get("device_id", "unknown")
        timestamp = data.get("timestamp", time.time())
        
        # 获取设备类型和规则
        device_type = get_device_type(device_id)
        rules = DEVICE_RULES.get(device_type, DEVICE_RULES.get("default", {}))
        
        # 准备LLM分析参数
        analysis_inputs = {
            "device_id": device_id,
            "temperature": data.get("temperature", data.get("cpu_temperature", "N/A")),
            "humidity": data.get("humidity", "N/A"),
            "additional_data": json.dumps({k: v for k, v in data.items() 
                                        if k not in ["device_id", "temperature", "humidity", "timestamp"]}),
            "timestamp": timestamp,
            "temp_high": rules.get("temp_high", 30.0),
            "temp_low": rules.get("temp_low", 18.0),
            "humidity_high": rules.get("humidity_high", 70.0),
            "humidity_low": rules.get("humidity_low", 30.0),
            "additional_rules": rules.get("additional_rules", "无其他规则")
        }
        
        # 使用LLM分析数据
        logger.info(f"分析设备 {device_id} 数据")
        analysis_result = analysis_chain.run(**analysis_inputs)
        
        # 解析LLM输出
        try:
            result_json = json.loads(analysis_result)
            logger.info(f"设备状态分析结果: {result_json['device_status']}")
            
            # 处理控制动作
            if "control_actions" in result_json and result_json["control_actions"]:
                handle_control_actions(result_json["control_actions"])
                
            # 发布分析结果到MQTT
            publish_analysis_result(device_id, result_json)
                
            return result_json
            
        except json.JSONDecodeError:
            logger.error(f"无法解析LLM输出为JSON: {analysis_result}")
            return {"error": "解析LLM输出失败", "raw_output": analysis_result}
            
    except Exception as e:
        logger.error(f"处理设备数据时出错: {str(e)}")
        return {"error": str(e)}

def get_device_type(device_id):
    """
    根据设备ID获取设备类型
    :param device_id: 设备ID
    :return: 设备类型
    """
    # 根据设备ID前缀判断类型
    if device_id.startswith("temp_"):
        return "temperature_sensor"
    elif device_id.startswith("hum_"):
        return "humidity_sensor"
    elif device_id.startswith("env_"):
        return "environmental_sensor"
    else:
        return "default"

def handle_control_actions(actions):
    """
    处理控制动作
    :param actions: 控制动作列表
    """
    from device_controller import execute_device_action
    from mqtt_client import get_mqtt_client
    
    mqtt_client = get_mqtt_client()
    
    for action in actions:
        device_id = action.get("device_id")
        action_type = action.get("action")
        parameters = action.get("parameters", {})
        
        logger.info(f"执行设备控制: 设备={device_id}, 动作={action_type}, 参数={parameters}")
        
        # 在新线程中执行设备控制，避免阻塞
        def execute_action():
            try:
                # 执行设备控制
                result = execute_device_action(device_id, action_type, parameters)
                
                # 发布控制结果到MQTT
                control_result = {
                    "device_id": device_id,
                    "action": action_type,
                    "parameters": parameters,
                    "result": result,
                    "timestamp": time.time()
                }
                
                mqtt_client.publish("device/control/result", control_result)
            except Exception as e:
                logger.error(f"执行设备控制时出错: {str(e)}")
        
        # 启动控制线程
        threading.Thread(target=execute_action).start()

def publish_analysis_result(device_id, result):
    """
    发布分析结果到MQTT
    :param device_id: 设备ID
    :param result: 分析结果
    """
    try:
        from mqtt_client import get_mqtt_client
        
        mqtt_client = get_mqtt_client()
        
        # 添加时间戳
        result["timestamp"] = time.time()
        result["device_id"] = device_id
        
        # 发布到分析结果主题
        mqtt_client.publish(f"device/{device_id}/analysis", result)
        logger.debug(f"已发布设备 {device_id} 的分析结果")
        
    except Exception as e:
        logger.error(f"发布分析结果时出错: {str(e)}")

if __name__ == "__main__":
    # 测试代码
    init_processor() 
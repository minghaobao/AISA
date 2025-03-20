import os
import re
import json
import logging
import time
from config import LOG_CONFIG, LLM_CONFIG, DEVICE_CONFIG
from langchain_community.llms import OpenAI
from langchain_community.chat_models import ChatOpenAI
from langchain.chains import LLMChain
from langchain.prompts.chat import ChatPromptTemplate
from influx_writer import write_to_influxdb
from alert_manager import check_and_send_alert

# 配置日志
logging.basicConfig(
    level=LOG_CONFIG["level"],
    format=LOG_CONFIG["format"],
    filename=LOG_CONFIG.get("filename")
)
logger = logging.getLogger("langchain_processor")

# 初始化LLM
llm = OpenAI(
    temperature=LLM_CONFIG["temperature"],
    openai_api_key=LLM_CONFIG["api_key"],
    model_name=LLM_CONFIG["model_name"]
)

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

# 创建分析提示模板
device_analysis_prompt = ChatPromptTemplate.from_template(DEVICE_ANALYSIS_TEMPLATE)

# 创建分析链
analysis_chain = LLMChain(
    llm=llm,
    prompt=device_analysis_prompt,
    verbose=LLM_CONFIG.get("verbose", False)
)

def process_device_data(topic, data):
    """
    处理设备数据
    :param topic: MQTT主题
    :param data: 设备数据字典
    :return: 处理结果
    """
    try:
        device_id = data.get("device_id", "unknown")
        timestamp = data.get("timestamp", time.time())
        
        # 记录数据到InfluxDB
        write_to_influxdb(device_id, data)
        
        # 检查是否需要发送警报
        check_and_send_alert(device_id, data)
        
        # 获取设备类型和规则
        device_type = get_device_type(device_id)
        rules = DEVICE_RULES.get(device_type, DEVICE_RULES["default"])
        
        # 准备LLM分析参数
        analysis_inputs = {
            "device_id": device_id,
            "temperature": data.get("temperature", "N/A"),
            "humidity": data.get("humidity", "N/A"),
            "additional_data": json.dumps({k: v for k, v in data.items() 
                                        if k not in ["device_id", "temperature", "humidity", "timestamp"]}),
            "timestamp": timestamp,
            "temp_high": rules["temp_high"],
            "temp_low": rules["temp_low"],
            "humidity_high": rules["humidity_high"],
            "humidity_low": rules["humidity_low"],
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

if __name__ == "__main__":
    # 测试代码
    test_data = {
        "device_id": "env_001",
        "temperature": 32.5,
        "humidity": 75.2,
        "light_level": 450,
        "air_quality": 95,
        "timestamp": time.time()
    }
    
    result = process_device_data("device/data", test_data)
    print(json.dumps(result, indent=2, ensure_ascii=False)) 
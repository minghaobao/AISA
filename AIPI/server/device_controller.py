import logging
import time
import json
from config import LOG_CONFIG, DEVICE_CONFIG

# 配置日志
logging.basicConfig(
    level=LOG_CONFIG["level"],
    format=LOG_CONFIG["format"],
    filename=LOG_CONFIG.get("filename")
)
logger = logging.getLogger("device_controller")

# 设备状态存储
device_status = {}

def init_devices():
    """
    初始化所有设备状态记录
    :return: 初始化是否成功
    """
    try:
        logger.info("正在初始化设备控制器...")
        
        # 初始化设备状态
        for device_id, config in DEVICE_CONFIG.items():
            device_status[device_id] = "off"  # 默认关闭状态
            logger.info(f"初始化设备状态: {device_id}")
            
        return True
    
    except Exception as e:
        logger.error(f"初始化设备控制器时出错: {str(e)}")
        return False

def execute_device_action(device_id, action, parameters=None):
    """
    在服务器端记录设备控制动作，实际控制由MQTT发送到设备执行
    :param device_id: 设备ID
    :param action: 动作类型（on/off/adjust等）
    :param parameters: 参数字典
    :return: 执行结果
    """
    if parameters is None:
        parameters = {}
        
    # 获取设备配置
    device_config = DEVICE_CONFIG.get(device_id)
    if not device_config:
        logger.error(f"未找到设备配置: {device_id}")
        return {"success": False, "error": "设备不存在"}
    
    # 检查设备类型和记录相应的控制
    device_type = device_config.get("type", "unknown")
    
    try:
        # 更新设备状态
        if action.lower() in ["on", "off"]:
            device_status[device_id] = action.lower()
        
        # 记录操作
        logger.info(f"记录设备控制: {device_id} ({device_type}) - 动作: {action}, 参数: {parameters}")
        
        # 在服务器端，我们只记录状态，实际控制由MQTT发送到设备
        return {
            "success": True, 
            "device_id": device_id,
            "action": action,
            "parameters": parameters,
            "status": "command_sent"
        }
            
    except Exception as e:
        logger.error(f"处理设备 {device_id} 命令时出错: {str(e)}")
        return {"success": False, "error": str(e)}

def get_device_status(device_id=None):
    """
    获取设备状态
    :param device_id: 设备ID，如果为None则返回所有设备状态
    :return: 设备状态字典
    """
    if device_id:
        return {device_id: device_status.get(device_id, "unknown")}
    else:
        return device_status

def cleanup():
    """
    清理设备控制器
    """
    logger.info("清理设备控制器...")
    # 服务器端不需要实际清理设备，只记录日志
    return True 
import logging
import time
import json
import threading
from config import LOG_CONFIG, DEVICE_CONFIG
import importlib.util

# 配置日志
logging.basicConfig(
    level=LOG_CONFIG["level"],
    format=LOG_CONFIG["format"],
    filename=LOG_CONFIG.get("filename")
)
logger = logging.getLogger("device_controller")

# 检测是否在树莓派环境
try:
    import RPi.GPIO as GPIO
    IS_RASPBERRY_PI = True
    
    # 设置GPIO模式
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    # 初始化设备引脚
    for device_id, config in DEVICE_CONFIG.items():
        if "gpio_pin" in config:
            GPIO.setup(config["gpio_pin"], GPIO.OUT)
            initial_state = GPIO.HIGH if config.get("initial_state", "off") == "off" else GPIO.LOW
            GPIO.output(config["gpio_pin"], initial_state)
            logger.info(f"初始化设备 {device_id} 在引脚 {config['gpio_pin']} 上")
    
except ImportError:
    IS_RASPBERRY_PI = False
    logger.warning("未检测到RPi.GPIO模块，将使用模拟模式运行")

# 设备状态存储
device_status = {}

def execute_device_action(device_id, action, parameters=None):
    """
    执行设备控制动作
    :param device_id: 设备ID
    :param action: 动作类型（on/off/adjust）
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
    
    # 检查设备类型和执行相应的控制
    device_type = device_config.get("type", "unknown")
    
    try:
        if device_type == "relay":
            return control_relay(device_id, device_config, action)
        elif device_type == "fan":
            return control_fan(device_id, device_config, action, parameters)
        elif device_type == "light":
            return control_light(device_id, device_config, action, parameters)
        elif device_type == "speaker":
            return control_speaker(device_id, device_config, action, parameters)
        elif device_type == "custom":
            return control_custom_device(device_id, device_config, action, parameters)
        else:
            logger.warning(f"未知设备类型: {device_type}")
            return {"success": False, "error": f"不支持的设备类型: {device_type}"}
            
    except Exception as e:
        logger.error(f"控制设备 {device_id} 时出错: {str(e)}")
        return {"success": False, "error": str(e)}

def control_relay(device_id, config, action):
    """控制继电器设备"""
    gpio_pin = config.get("gpio_pin")
    
    if not gpio_pin:
        return {"success": False, "error": "设备配置缺少GPIO引脚"}
    
    if action.lower() == "on":
        set_gpio_state(gpio_pin, config.get("on_value", GPIO.LOW))
        device_status[device_id] = "on"
        return {"success": True, "state": "on"}
    
    elif action.lower() == "off":
        set_gpio_state(gpio_pin, config.get("off_value", GPIO.HIGH))
        device_status[device_id] = "off"
        return {"success": True, "state": "off"}
    
    else:
        return {"success": False, "error": f"继电器设备不支持动作: {action}"}

def control_fan(device_id, config, action, parameters):
    """控制风扇设备（可调速）"""
    gpio_pin = config.get("gpio_pin")
    pwm_pin = config.get("pwm_pin")
    
    if not gpio_pin:
        return {"success": False, "error": "设备配置缺少GPIO引脚"}
    
    if action.lower() == "on":
        set_gpio_state(gpio_pin, config.get("on_value", GPIO.LOW))
        device_status[device_id] = "on"
        
        # 如果有PWM引脚和速度参数，则设置速度
        if pwm_pin and "speed" in parameters:
            speed = int(parameters["speed"])
            if IS_RASPBERRY_PI:
                try:
                    pwm = GPIO.PWM(pwm_pin, 100)  # 频率100Hz
                    pwm.start(speed)
                except Exception as e:
                    logger.error(f"设置风扇速度时出错: {str(e)}")
            else:
                logger.info(f"模拟设置风扇速度: {speed}%")
                
        return {"success": True, "state": "on", "speed": parameters.get("speed", 100)}
    
    elif action.lower() == "off":
        set_gpio_state(gpio_pin, config.get("off_value", GPIO.HIGH))
        device_status[device_id] = "off"
        return {"success": True, "state": "off"}
    
    elif action.lower() == "adjust":
        if "speed" in parameters and pwm_pin:
            speed = int(parameters["speed"])
            if IS_RASPBERRY_PI:
                try:
                    pwm = GPIO.PWM(pwm_pin, 100)  # 频率100Hz
                    pwm.ChangeDutyCycle(speed)
                except Exception as e:
                    logger.error(f"调整风扇速度时出错: {str(e)}")
            else:
                logger.info(f"模拟调整风扇速度: {speed}%")
            return {"success": True, "state": "adjusted", "speed": speed}
        else:
            return {"success": False, "error": "调整风扇需要指定速度参数"}
    
    else:
        return {"success": False, "error": f"风扇设备不支持动作: {action}"}

def control_light(device_id, config, action, parameters):
    """控制灯光设备（可调亮度/颜色）"""
    gpio_pin = config.get("gpio_pin")
    
    if not gpio_pin:
        return {"success": False, "error": "设备配置缺少GPIO引脚"}
    
    if action.lower() == "on":
        set_gpio_state(gpio_pin, config.get("on_value", GPIO.LOW))
        device_status[device_id] = "on"
        
        # 处理亮度参数
        brightness = parameters.get("brightness", 100)
        
        return {"success": True, "state": "on", "brightness": brightness}
    
    elif action.lower() == "off":
        set_gpio_state(gpio_pin, config.get("off_value", GPIO.HIGH))
        device_status[device_id] = "off"
        return {"success": True, "state": "off"}
    
    elif action.lower() == "adjust":
        if "brightness" in parameters:
            brightness = int(parameters["brightness"])
            logger.info(f"调整灯光亮度: {brightness}%")
            return {"success": True, "state": "adjusted", "brightness": brightness}
        elif "color" in parameters:
            color = parameters["color"]
            logger.info(f"调整灯光颜色: {color}")
            return {"success": True, "state": "adjusted", "color": color}
        else:
            return {"success": False, "error": "调整灯光需要指定亮度或颜色参数"}
    
    else:
        return {"success": False, "error": f"灯光设备不支持动作: {action}"}

def control_speaker(device_id, config, action, parameters):
    """控制扬声器设备（文本转语音）"""
    if action.lower() == "speak":
        if "text" in parameters:
            text = parameters["text"]
            volume = parameters.get("volume", 80)
            
            # 模拟TTS
            logger.info(f"播放语音: {text} (音量: {volume}%)")
            
            # 实际环境中使用树莓派播放语音
            if IS_RASPBERRY_PI and importlib.util.find_spec("gtts"):
                try:
                    from gtts import gTTS
                    import os
                    
                    tts = gTTS(text=text, lang=parameters.get("language", "zh"))
                    tts.save("temp_speech.mp3")
                    os.system(f"mpg321 -g {volume} temp_speech.mp3")
                    
                except Exception as e:
                    logger.error(f"播放语音时出错: {str(e)}")
            
            return {"success": True, "action": "speak", "text": text}
        else:
            return {"success": False, "error": "播放语音需要提供文本内容"}
    
    else:
        return {"success": False, "error": f"扬声器设备不支持动作: {action}"}

def control_custom_device(device_id, config, action, parameters):
    """控制自定义设备"""
    # 获取自定义控制脚本路径
    script_path = config.get("script_path")
    
    if not script_path:
        return {"success": False, "error": "自定义设备缺少脚本路径配置"}
    
    try:
        # 异步执行自定义脚本
        def run_script():
            import subprocess
            cmd = [
                "python", script_path, 
                "--device", device_id,
                "--action", action
            ]
            
            # 添加参数
            for key, value in parameters.items():
                cmd.extend([f"--{key}", str(value)])
                
            subprocess.run(cmd)
        
        # 创建线程异步执行
        thread = threading.Thread(target=run_script)
        thread.daemon = True
        thread.start()
        
        return {"success": True, "action": action, "async": True}
        
    except Exception as e:
        logger.error(f"执行自定义设备脚本时出错: {str(e)}")
        return {"success": False, "error": str(e)}

def set_gpio_state(pin, state):
    """设置GPIO引脚状态"""
    if IS_RASPBERRY_PI:
        GPIO.output(pin, state)
    else:
        logger.info(f"模拟设置GPIO引脚 {pin} 状态为 {state}")

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
    """清理GPIO资源"""
    if IS_RASPBERRY_PI:
        GPIO.cleanup()
    logger.info("GPIO资源已清理")

if __name__ == "__main__":
    # 测试代码
    try:
        print("测试设备控制...")
        
        # 测试继电器控制
        result1 = execute_device_action("relay_1", "on")
        print(f"控制继电器开启: {result1}")
        
        time.sleep(2)
        
        result2 = execute_device_action("relay_1", "off")
        print(f"控制继电器关闭: {result2}")
        
        # 测试风扇控制
        result3 = execute_device_action("fan_1", "on", {"speed": 80})
        print(f"控制风扇开启: {result3}")
        
        time.sleep(2)
        
        result4 = execute_device_action("fan_1", "off")
        print(f"控制风扇关闭: {result4}")
        
    finally:
        # 清理资源
        cleanup() 
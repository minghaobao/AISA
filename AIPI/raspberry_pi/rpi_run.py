#!/usr/bin/env python
import os
import sys
import time
import logging
import threading
import argparse

# 设置当前目录为工作目录
current_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(current_dir)

# 确保当前目录在搜索路径中
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# 导入本地配置
from config import LOG_CONFIG, DEVICE_ID

# 配置日志
logging.basicConfig(
    level=LOG_CONFIG["level"],
    format=LOG_CONFIG["format"],
    filename=LOG_CONFIG.get("filename")
)
logger = logging.getLogger("rpi_main")

def start_mqtt_client():
    """启动MQTT客户端"""
    # 使用绝对导入
    from mqtt_client import get_mqtt_client
    
    logger.info("正在启动MQTT客户端...")
    mqtt_client = get_mqtt_client()
    
    # 连接MQTT代理服务器
    if mqtt_client.connect():
        logger.info("MQTT客户端启动成功")
        return mqtt_client
    else:
        logger.error("MQTT客户端启动失败")
        return None

def start_device_controller():
    """初始化设备控制器"""
    from device_controller import init_devices
    
    logger.info("正在初始化设备控制器...")
    if init_devices():
        logger.info("设备控制器初始化成功")
        return True
    else:
        logger.error("设备控制器初始化失败")
        return False

def start_langchain_processor(background=True):
    """
    启动LangChain处理器
    :param background: 是否在后台运行
    """
    from langchain_processor import init_processor
    
    logger.info("正在启动LangChain处理器...")
    
    if background:
        # 创建新线程运行处理器
        processor_thread = threading.Thread(target=init_processor)
        processor_thread.daemon = True
        processor_thread.start()
        logger.info("LangChain处理器在后台启动")
        return processor_thread
    else:
        # 在主线程运行处理器
        logger.info("LangChain处理器在主线程启动")
        init_processor()
        return None

def cleanup():
    """清理资源"""
    from device_controller import cleanup as device_cleanup
    
    logger.info("正在清理资源...")
    
    # 清理设备控制相关资源
    device_cleanup()
    
    logger.info("资源清理完成")

def run_all_services():
    """运行所有树莓派端服务"""
    try:
        # 初始化设备控制器
        if not start_device_controller():
            logger.warning("设备控制器初始化失败，但将继续启动其他服务")
        
        # 启动MQTT客户端
        mqtt_client = start_mqtt_client()
        if not mqtt_client:
            logger.error("无法启动MQTT客户端，程序退出")
            return False
            
        # 启动LangChain处理器（后台）
        processor_thread = start_langchain_processor(background=True)
        
        logger.info(f"所有树莓派端服务已启动 (设备ID: {DEVICE_ID})，按Ctrl+C退出")
        
        # 保持主线程运行
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("接收到退出信号")
        
        # 清理资源
        cleanup()
        
        # 断开MQTT连接
        if mqtt_client:
            mqtt_client.disconnect()
            
        return True
        
    except Exception as e:
        logger.error(f"运行服务时出错: {str(e)}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="树莓派端 AI MQTT LangChain 服务")
    parser.add_argument("--mqtt", action="store_true", help="只启动MQTT客户端")
    parser.add_argument("--device", action="store_true", help="只初始化设备控制器")
    parser.add_argument("--processor", action="store_true", help="只启动LangChain处理器")
    parser.add_argument("--all", action="store_true", help="启动所有服务")
    
    args = parser.parse_args()
    
    try:
        if args.mqtt:
            # 只启动MQTT客户端
            mqtt_client = start_mqtt_client()
            
            if mqtt_client:
                logger.info("MQTT客户端已启动，按Ctrl+C退出")
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    mqtt_client.disconnect()
                    logger.info("MQTT客户端已停止")
                    
        elif args.device:
            # 只初始化设备控制器
            start_device_controller()
            logger.info("设备控制器已初始化，按Ctrl+C退出")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("设备控制器已停止")
                
        elif args.processor:
            # 只启动LangChain处理器
            start_langchain_processor(background=False)
            
        elif args.all or not (args.mqtt or args.device or args.processor):
            # 启动所有服务
            success = run_all_services()
            sys.exit(0 if success else 1)
            
        else:
            parser.print_help()
            
    except KeyboardInterrupt:
        logger.info("程序已被用户中断")
        
    except Exception as e:
        logger.error(f"程序运行时出错: {str(e)}")
        sys.exit(1)
        
    finally:
        cleanup() 
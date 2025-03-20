#!/usr/bin/env python
import os
import sys
import time
import logging
import threading
import argparse
from config import LOG_CONFIG

# 配置日志
logging.basicConfig(
    level=LOG_CONFIG["level"],
    format=LOG_CONFIG["format"],
    filename=LOG_CONFIG.get("filename")
)
logger = logging.getLogger("main")

def start_mqtt_client():
    """启动MQTT客户端"""
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

def start_web_server(background=True):
    """
    启动Web服务器
    :param background: 是否在后台运行
    """
    from web_control import start_web_server as web_start
    
    logger.info("正在启动Web服务器...")
    
    if background:
        # 创建新线程运行Web服务器
        web_thread = threading.Thread(target=web_start)
        web_thread.daemon = True
        web_thread.start()
        logger.info("Web服务器在后台启动")
        return web_thread
    else:
        # 在主线程运行Web服务器
        logger.info("Web服务器在主线程启动")
        web_start()

def start_api_server(background=True):
    """
    启动API服务器
    :param background: 是否在后台运行
    """
    import subprocess
    import sys
    
    logger.info("正在启动API服务器...")
    
    if background:
        # 创建一个子进程运行API服务器
        api_process = subprocess.Popen([sys.executable, "api-web.py"], 
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)
        logger.info("API服务器在后台启动，PID: %s", api_process.pid)
        return api_process
    else:
        # 在主线程运行API服务器
        logger.info("API服务器在主线程启动")
        os.system(f"{sys.executable} api-web.py")

def start_alert_checker(background=True):
    """
    启动告警检查服务
    :param background: 是否在后台运行
    """
    from alert_check import run_scheduled_checks
    
    logger.info("正在启动告警检查服务...")
    
    if background:
        # 创建新线程运行告警检查
        alert_thread = threading.Thread(target=run_scheduled_checks)
        alert_thread.daemon = True
        alert_thread.start()
        logger.info("告警检查服务在后台启动")
        return alert_thread
    else:
        # 在主线程运行告警检查
        logger.info("告警检查服务在主线程启动")
        run_scheduled_checks()
        return None

def cleanup():
    """清理资源"""
    from device_controller import cleanup as device_cleanup
    from influx_writer import close_connection as influx_close
    
    logger.info("正在清理资源...")
    
    # 清理设备控制相关资源
    device_cleanup()
    
    # 关闭InfluxDB连接
    influx_close()
    
    logger.info("资源清理完成")

def run_all_services():
    """运行所有服务"""
    try:
        # 启动MQTT客户端
        mqtt_client = start_mqtt_client()
        if not mqtt_client:
            logger.error("无法启动MQTT客户端，程序退出")
            return False
            
        # 启动Web服务器（后台）
        web_thread = start_web_server(background=True)
        
        # 启动API服务器（后台）
        api_process = start_api_server(background=True)
        
        # 启动告警检查（后台）
        alert_thread = start_alert_checker(background=True)
        
        logger.info("所有服务已启动，按Ctrl+C退出")
        
        # 保持主线程运行
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("接收到退出信号")
        
        # 清理资源
        cleanup()
        
        # 终止API进程
        if api_process:
            logger.info("正在终止API服务器进程...")
            api_process.terminate()
            api_process.wait()
            
        # 断开MQTT连接
        if mqtt_client:
            mqtt_client.disconnect()
            
        return True
        
    except Exception as e:
        logger.error(f"运行服务时出错: {str(e)}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI MQTT LangChain平台启动器")
    parser.add_argument("--mqtt", action="store_true", help="只启动MQTT客户端")
    parser.add_argument("--web", action="store_true", help="只启动Web服务器")
    parser.add_argument("--api", action="store_true", help="只启动API服务器")
    parser.add_argument("--alert", action="store_true", help="只启动告警检查服务")
    parser.add_argument("--all", action="store_true", help="启动所有服务")
    
    args = parser.parse_args()
    
    try:
        if args.mqtt:
            # 只启动MQTT客户端
            mqtt_client = start_mqtt_client()
            if not mqtt_client:
                logger.error("无法启动MQTT客户端，程序退出")
                sys.exit(1)
                
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("接收到退出信号")
                
            if mqtt_client:
                mqtt_client.disconnect()
                
        elif args.web:
            # 只启动Web服务器
            start_web_server(background=False)
            
        elif args.api:
            # 只启动API服务器
            start_api_server(background=False)
            
        elif args.alert:
            # 只启动告警检查服务
            start_alert_checker(background=False)
            
        else:
            # 默认启动所有服务
            run_all_services()
            
    except Exception as e:
        logger.error(f"启动服务时出错: {str(e)}")
        sys.exit(1)
        
    finally:
        cleanup() 
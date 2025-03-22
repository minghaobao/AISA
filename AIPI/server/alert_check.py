import logging
import time
import json
import argparse
import schedule
from datetime import datetime
from config import LOG_CONFIG, ALERT_CONFIG
from influx_writer import query_latest_data
from alert_manager import check_and_send_alert
from influx_writer import write_event_to_influxdb

# 配置日志
logging.basicConfig(
    level=LOG_CONFIG["level"],
    format=LOG_CONFIG["format"],
    filename=LOG_CONFIG.get("filename")
)
logger = logging.getLogger("alert_check")

def check_device(device_id):
    """
    检查单个设备的最新数据
    :param device_id: 设备ID
    :return: 是否发送了告警
    """
    try:
        # 从InfluxDB获取最新数据
        latest_data = query_latest_data(device_id, time_range="10m")
        
        if not latest_data:
            logger.warning(f"未找到设备 {device_id} 的最新数据")
            
            # 检查设备是否应该处于活动状态
            now = datetime.now()
            hour = now.hour
            
            # 获取设备活动时间配置
            device_config = ALERT_CONFIG.get("device_activity", {}).get(device_id, {})
            active_hours = device_config.get("active_hours", [0, 23])  # 默认全天活动
            
            # 如果当前时间在活动时间范围内，但没有数据，可能发生了通信故障
            if active_hours[0] <= hour <= active_hours[1]:
                # 检查最后一次心跳时间
                if "last_heartbeat" in device_config:
                    last_hb = datetime.fromtimestamp(device_config["last_heartbeat"])
                    time_diff = (now - last_hb).total_seconds() / 60  # 分钟
                    
                    # 如果超过预期通信间隔，发送通信故障告警
                    if time_diff > device_config.get("expected_interval_minutes", 5):
                        alert_data = {
                            "device_id": device_id,
                            "error": "通信故障",
                            "last_heartbeat": device_config["last_heartbeat"],
                            "time_since_last": f"{time_diff:.1f}分钟",
                            "timestamp": time.time()
                        }
                        
                        # 创建通信故障事件
                        write_event_to_influxdb(
                            "communication_failure", 
                            device_id, 
                            f"设备 {device_id} 已 {time_diff:.1f} 分钟未通信",
                            "error"
                        )
                        
                        # 发送通信故障告警
                        check_and_send_alert(device_id, alert_data)
                        logger.error(f"设备 {device_id} 通信故障，已 {time_diff:.1f} 分钟未收到数据")
                        return True
            
            return False
            
        # 添加设备ID到数据中
        latest_data["device_id"] = device_id
        
        # 如果数据中没有时间戳，使用当前时间
        if "timestamp" not in latest_data:
            latest_data["timestamp"] = time.time()
            
        # 检查数据并发送告警
        result = check_and_send_alert(device_id, latest_data)
        
        if result:
            logger.info(f"设备 {device_id} 触发了告警")
        else:
            logger.debug(f"设备 {device_id} 状态正常")
            
        return result
        
    except Exception as e:
        logger.error(f"检查设备 {device_id} 时出错: {str(e)}")
        return False

def check_all_devices():
    """检查所有配置的设备"""
    # 获取所有需要检查的设备ID
    device_ids = set()
    
    # 从设备规则中获取设备ID
    for device_id in ALERT_CONFIG.get("device_rules", {}):
        device_ids.add(device_id)
        
    # 从设备活动时间配置中获取设备ID
    for device_id in ALERT_CONFIG.get("device_activity", {}):
        device_ids.add(device_id)
        
    # 添加额外配置的设备
    for device_id in ALERT_CONFIG.get("additional_devices", []):
        device_ids.add(device_id)
        
    logger.info(f"开始检查 {len(device_ids)} 个设备")
    
    alert_count = 0
    for device_id in device_ids:
        if check_device(device_id):
            alert_count += 1
            
    logger.info(f"设备检查完成，触发了 {alert_count} 个告警")
    return alert_count

def run_scheduled_checks():
    """运行定时检查任务"""
    logger.info("启动定时告警检查服务")
    
    # 设置定时任务
    schedule_interval = ALERT_CONFIG.get("check_interval_minutes", 5)
    logger.info(f"设置定时检查间隔: {schedule_interval} 分钟")
    
    schedule.every(schedule_interval).minutes.do(check_all_devices)
    
    # 立即执行一次
    check_all_devices()
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("定时检查服务已停止")
    except Exception as e:
        logger.error(f"定时检查服务出错: {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="设备告警检查工具")
    parser.add_argument("--device", help="要检查的设备ID")
    parser.add_argument("--all", action="store_true", help="检查所有设备")
    parser.add_argument("--daemon", action="store_true", help="以守护进程方式运行定时检查")
    
    args = parser.parse_args()
    
    if args.device:
        # 检查单个设备
        result = check_device(args.device)
        print(f"设备 {args.device} 检查结果: {'已触发告警' if result else '状态正常'}")
    elif args.all:
        # 检查所有设备
        count = check_all_devices()
        print(f"检查完成，触发了 {count} 个告警")
    elif args.daemon:
        # 以守护进程方式运行
        run_scheduled_checks()
    else:
        # 如果没有指定参数，显示帮助
        parser.print_help() 
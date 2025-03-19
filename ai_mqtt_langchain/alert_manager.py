import logging
import time
import json
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import ALERT_CONFIG, LOG_CONFIG
from influx_writer import write_event_to_influxdb

# 配置日志
logging.basicConfig(
    level=LOG_CONFIG["level"],
    format=LOG_CONFIG["format"],
    filename=LOG_CONFIG.get("filename")
)
logger = logging.getLogger("alert_manager")

# 告警历史记录，防止重复告警
alert_history = {}
# 告警冷却时间（秒）
ALERT_COOLDOWN = ALERT_CONFIG.get("cooldown_seconds", 300)  # 默认5分钟

def check_and_send_alert(device_id, data):
    """
    检查设备数据并在需要时发送告警
    :param device_id: 设备ID
    :param data: 设备数据
    :return: 是否发送了告警
    """
    try:
        # 获取设备特定的告警规则
        device_rules = get_device_alert_rules(device_id)
        if not device_rules:
            return False
            
        # 检查每条规则
        for rule in device_rules:
            rule_name = rule.get("name", "未命名规则")
            field = rule.get("field")
            condition = rule.get("condition")
            threshold = rule.get("threshold")
            severity = rule.get("severity", "warning")
            
            # 检查数据中是否包含要监控的字段
            if field not in data:
                continue
                
            value = data[field]
            alert_triggered = False
            
            # 检查条件
            if condition == "greater_than" and float(value) > float(threshold):
                alert_triggered = True
                message = f"设备 {device_id} 的 {field} 值 ({value}) 超过阈值 {threshold}"
            elif condition == "less_than" and float(value) < float(threshold):
                alert_triggered = True
                message = f"设备 {device_id} 的 {field} 值 ({value}) 低于阈值 {threshold}"
            elif condition == "equals" and str(value) == str(threshold):
                alert_triggered = True
                message = f"设备 {device_id} 的 {field} 值等于 {threshold}"
            elif condition == "not_equals" and str(value) != str(threshold):
                alert_triggered = True
                message = f"设备 {device_id} 的 {field} 值 ({value}) 不等于期望值 {threshold}"
            
            # 如果触发告警，发送通知
            if alert_triggered:
                # 检查是否在冷却期内
                alert_key = f"{device_id}_{rule_name}"
                current_time = time.time()
                
                if alert_key in alert_history:
                    last_alert_time = alert_history[alert_key]
                    if current_time - last_alert_time < ALERT_COOLDOWN:
                        logger.debug(f"告警 {alert_key} 在冷却期内，跳过")
                        continue
                
                # 发送告警
                send_alert(device_id, rule_name, message, severity, data)
                
                # 记录告警历史
                alert_history[alert_key] = current_time
                
                # 记录事件到InfluxDB
                write_event_to_influxdb(
                    "alert", 
                    device_id, 
                    message,
                    severity
                )
                
                return True
                
    except Exception as e:
        logger.error(f"检查告警时出错: {str(e)}")
        
    return False

def get_device_alert_rules(device_id):
    """
    获取设备的告警规则
    :param device_id: 设备ID
    :return: 规则列表
    """
    # 首先检查设备特定规则
    if device_id in ALERT_CONFIG["device_rules"]:
        return ALERT_CONFIG["device_rules"][device_id]
    
    # 然后检查设备类型规则
    device_type = None
    if device_id.startswith("temp_"):
        device_type = "temperature_sensor"
    elif device_id.startswith("hum_"):
        device_type = "humidity_sensor"
    elif device_id.startswith("env_"):
        device_type = "environmental_sensor"
    
    if device_type and device_type in ALERT_CONFIG["type_rules"]:
        return ALERT_CONFIG["type_rules"][device_type]
    
    # 最后返回默认规则
    return ALERT_CONFIG["default_rules"]

def send_alert(device_id, rule_name, message, severity, data):
    """
    发送告警通知
    :param device_id: 设备ID
    :param rule_name: 规则名称
    :param message: 告警消息
    :param severity: 严重性
    :param data: 设备数据
    """
    # 构建告警信息
    alert_info = {
        "device_id": device_id,
        "rule": rule_name,
        "message": message,
        "severity": severity,
        "timestamp": time.time(),
        "data": data
    }
    
    alert_text = json.dumps(alert_info, indent=2, ensure_ascii=False)
    logger.warning(f"触发告警: {message}")
    
    # 发送邮件告警
    if ALERT_CONFIG.get("email", {}).get("enabled", False):
        send_email_alert(alert_info)
    
    # 发送Telegram告警
    if ALERT_CONFIG.get("telegram", {}).get("enabled", False):
        send_telegram_alert(alert_info)
    
    # 记录到日志文件
    if ALERT_CONFIG.get("log_file", {}).get("enabled", False):
        log_alert_to_file(alert_info)

def send_email_alert(alert_info):
    """发送邮件告警"""
    try:
        email_config = ALERT_CONFIG.get("email", {})
        if not email_config.get("enabled", False):
            return False
            
        # 创建邮件内容
        msg = MIMEMultipart()
        msg['Subject'] = f"[{alert_info['severity'].upper()}] 设备告警: {alert_info['device_id']}"
        msg['From'] = email_config["sender"]
        msg['To'] = ", ".join(email_config["recipients"])
        
        # 邮件正文
        html_body = f"""
        <html>
        <body>
            <h2>设备告警通知</h2>
            <p><strong>设备ID:</strong> {alert_info['device_id']}</p>
            <p><strong>规则:</strong> {alert_info['rule']}</p>
            <p><strong>消息:</strong> {alert_info['message']}</p>
            <p><strong>严重性:</strong> {alert_info['severity']}</p>
            <p><strong>时间:</strong> {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(alert_info['timestamp']))}</p>
            <h3>设备数据:</h3>
            <pre>{json.dumps(alert_info['data'], indent=2, ensure_ascii=False)}</pre>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(html_body, 'html'))
        
        # 连接SMTP服务器并发送
        server = smtplib.SMTP(email_config["smtp_server"], email_config["smtp_port"])
        if email_config.get("use_tls", False):
            server.starttls()
        
        if email_config.get("username") and email_config.get("password"):
            server.login(email_config["username"], email_config["password"])
            
        server.send_message(msg)
        server.quit()
        
        logger.info(f"已发送邮件告警至 {', '.join(email_config['recipients'])}")
        return True
        
    except Exception as e:
        logger.error(f"发送邮件告警时出错: {str(e)}")
        return False

def send_telegram_alert(alert_info):
    """发送Telegram告警"""
    try:
        telegram_config = ALERT_CONFIG.get("telegram", {})
        if not telegram_config.get("enabled", False):
            return False
            
        bot_token = telegram_config["bot_token"]
        chat_ids = telegram_config["chat_ids"]
        
        # 消息格式化
        message = f"""
🚨 *设备告警通知*
*设备ID:* {alert_info['device_id']}
*规则:* {alert_info['rule']}
*消息:* {alert_info['message']}
*严重性:* {alert_info['severity']}
*时间:* {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(alert_info['timestamp']))}

*设备数据:*
```
{json.dumps(alert_info['data'], indent=2, ensure_ascii=False)}
```
        """
        
        # 发送到每个聊天ID
        for chat_id in chat_ids:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            
            response = requests.post(url, json=payload)
            response.raise_for_status()
            
        logger.info(f"已发送Telegram告警至 {len(chat_ids)} 个接收者")
        return True
        
    except Exception as e:
        logger.error(f"发送Telegram告警时出错: {str(e)}")
        return False

def log_alert_to_file(alert_info):
    """记录告警到文件"""
    try:
        log_config = ALERT_CONFIG.get("log_file", {})
        if not log_config.get("enabled", False):
            return False
            
        log_path = log_config.get("path", "alerts.log")
        
        # 格式化日志条目
        log_entry = (
            f"[{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(alert_info['timestamp']))}] "
            f"[{alert_info['severity'].upper()}] "
            f"设备: {alert_info['device_id']}, "
            f"规则: {alert_info['rule']}, "
            f"消息: {alert_info['message']}\n"
        )
        
        # 写入日志文件
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(log_entry)
            
        logger.info(f"已记录告警到文件: {log_path}")
        return True
        
    except Exception as e:
        logger.error(f"记录告警到文件时出错: {str(e)}")
        return False

if __name__ == "__main__":
    # 测试代码
    test_data = {
        "device_id": "temp_sensor_001",
        "temperature": 35.5,  # 高温触发告警
        "humidity": 25.0,     # 低湿度触发告警
        "timestamp": time.time()
    }
    
    result = check_and_send_alert("temp_sensor_001", test_data)
    print(f"告警检查结果: {result}") 
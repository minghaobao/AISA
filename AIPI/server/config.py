import os
import logging
from dotenv import load_dotenv

# 获取当前文件所在的目录
current_dir = os.path.dirname(os.path.abspath(__file__))

# 加载环境变量（首先尝试加载.env.local，然后加载.env）
env_local_path = os.path.join(current_dir, '.env.local')
env_path = os.path.join(current_dir, '.env')

if os.path.exists(env_local_path):
    load_dotenv(env_local_path)
    
load_dotenv(env_path)

# 确保日志目录存在
log_file = os.getenv("LOG_FILE", "logs/server.log")
if log_file:
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

# 日志配置
LOG_CONFIG = {
    "level": getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "filename": log_file
}

# MQTT配置
MQTT_CONFIG = {
    "broker_host": os.getenv("MQTT_HOST", "localhost"),
    "broker_port": int(os.getenv("MQTT_PORT", "1883")),
    "username": os.getenv("MQTT_USERNAME", ""),
    "password": os.getenv("MQTT_PASSWORD", ""),
    "keep_alive": int(os.getenv("MQTT_KEEP_ALIVE", "60")),
    "subscribe_topics": [
        "device/+/data",       # 设备数据主题，+是通配符
        "device/+/status",     # 设备状态主题
        "device/+/result",     # 设备命令结果主题
        "langchain/process/+", # LangChain处理请求
        "device/control/#"      # 设备控制主题，#是多级通配符
    ],
    "publish_topics": {
        "device_control": "device/control",
        "device_command": "device/{device_id}/command",  # 格式化字符串，将在使用时替换{device_id}
        "device_status": "device/status",
        "alert": "alert"
    }
}

# 设备IDs
DEVICE_IDS = os.getenv("DEVICE_IDS", "").split(",")

# LLM配置
LLM_CONFIG = {
    "api_key": os.getenv("OPENAI_API_KEY", ""),
    "model_name": os.getenv("LLM_MODEL", "gpt-3.5-turbo"),
    "temperature": float(os.getenv("LLM_TEMPERATURE", "0.1")),
    "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "1024")),
    "verbose": os.getenv("LLM_VERBOSE", "False").lower() == "true"
}

# 设备规则配置
DEVICE_RULES = {
    "default": {
        "temp_high": 30.0,
        "temp_low": 18.0,
        "humidity_high": 70.0,
        "humidity_low": 30.0,
        "additional_rules": "如果空气质量指数超过100，需要开启空气净化器"
    },
    "temperature_sensor": {
        "temp_high": 28.0,
        "temp_low": 18.0,
        "humidity_high": 65.0,
        "humidity_low": 35.0,
        "additional_rules": "如果温度波动过大，需要进行稳定控制"
    },
    "humidity_sensor": {
        "temp_high": 30.0,
        "temp_low": 20.0,
        "humidity_high": 60.0,
        "humidity_low": 40.0,
        "additional_rules": "如果湿度波动过大，需要进行稳定控制"
    },
    "environmental_sensor": {
        "temp_high": 26.0,
        "temp_low": 20.0,
        "humidity_high": 60.0,
        "humidity_low": 40.0,
        "additional_rules": "如果二氧化碳浓度超过1000ppm，需要增加通风"
    }
}

# 设备配置
DEVICE_CONFIG = {
    # 继电器设备
    "relay_1": {
        "type": "relay",
        "gpio_pin": 17,
        "description": "主电源继电器",
        "initial_state": "off"
    },
    "relay_2": {
        "type": "relay",
        "gpio_pin": 18,
        "description": "备用电源继电器",
        "initial_state": "off"
    },
    
    # 风扇设备
    "fan_1": {
        "type": "fan",
        "gpio_pin": 22,
        "pwm_pin": 23,  # PWM控制引脚
        "description": "主风扇",
        "initial_state": "off"
    },
    
    # 灯光设备
    "light_1": {
        "type": "light",
        "gpio_pin": 24,
        "description": "主照明灯",
        "initial_state": "off"
    },
    
    # 扬声器设备
    "speaker_1": {
        "type": "speaker",
        "description": "语音播报设备"
    }
}

# InfluxDB配置
INFLUXDB_CONFIG = {
    "url": os.getenv("INFLUXDB_URL", "http://localhost:8086"),
    "token": os.getenv("INFLUXDB_TOKEN", ""),
    "org": os.getenv("INFLUXDB_ORG", "smart_iot"),
    "bucket": os.getenv("INFLUXDB_BUCKET", "device_data"),
    "measurement": "sensors"
}

# 告警配置
ALERT_CONFIG = {
    "cooldown_seconds": int(os.getenv("ALERT_COOLDOWN", "300")),
    "check_interval_minutes": int(os.getenv("ALERT_CHECK_INTERVAL", "5")),
    
    # 默认告警规则
    "default_rules": [
        {
            "name": "高温告警",
            "field": "temperature",
            "condition": "greater_than",
            "threshold": 30.0,
            "severity": "warning"
        },
        {
            "name": "低温告警",
            "field": "temperature",
            "condition": "less_than",
            "threshold": 5.0,
            "severity": "warning"
        },
        {
            "name": "高湿度告警",
            "field": "humidity",
            "condition": "greater_than",
            "threshold": 80.0,
            "severity": "warning"
        },
        {
            "name": "低湿度告警",
            "field": "humidity",
            "condition": "less_than",
            "threshold": 20.0,
            "severity": "warning"
        }
    ],
    
    # 按设备类型的告警规则
    "type_rules": {
        "temperature_sensor": [
            {
                "name": "温度传感器高温告警",
                "field": "temperature",
                "condition": "greater_than",
                "threshold": 28.0,
                "severity": "warning"
            },
            {
                "name": "温度传感器低温告警",
                "field": "temperature",
                "condition": "less_than",
                "threshold": 10.0,
                "severity": "warning"
            }
        ],
        "environmental_sensor": [
            {
                "name": "环境传感器高二氧化碳告警",
                "field": "co2",
                "condition": "greater_than",
                "threshold": 1000.0,
                "severity": "warning"
            },
            {
                "name": "环境传感器空气质量告警",
                "field": "air_quality",
                "condition": "greater_than",
                "threshold": 100.0,
                "severity": "warning"
            }
        ]
    },
    
    # 按设备ID的告警规则
    "device_rules": {
        "env_001": [
            {
                "name": "特定设备高温告警",
                "field": "temperature",
                "condition": "greater_than",
                "threshold": 25.0,
                "severity": "warning"
            },
            {
                "name": "特定设备CO2告警",
                "field": "co2",
                "condition": "greater_than",
                "threshold": 1000.0,
                "severity": "danger"
            }
        ]
    },
    
    # 设备活动时间配置
    "device_activity": {
        "env_001": {
            "active_hours": [8, 20],  # 活动时间范围（小时）
            "expected_interval_minutes": 5,  # 预期通信间隔（分钟）
            "last_heartbeat": None  # 最后一次心跳时间（运行时更新）
        }
    },
    
    # 额外需要监控的设备列表
    "additional_devices": [
        "temp_sensor_001",
        "hum_sensor_001"
    ],
    
    # 邮件告警配置
    "email": {
        "enabled": os.getenv("EMAIL_ALERT_ENABLED", "False").lower() == "true",
        "sender": os.getenv("EMAIL_SENDER", "alerts@example.com"),
        "recipients": os.getenv("EMAIL_RECIPIENTS", "admin@example.com").split(","),
        "smtp_server": os.getenv("EMAIL_SMTP_SERVER", "smtp.example.com"),
        "smtp_port": int(os.getenv("EMAIL_SMTP_PORT", "587")),
        "use_tls": os.getenv("EMAIL_USE_TLS", "True").lower() == "true",
        "username": os.getenv("EMAIL_USERNAME", ""),
        "password": os.getenv("EMAIL_PASSWORD", "")
    },
    
    # Telegram告警配置
    "telegram": {
        "enabled": os.getenv("TELEGRAM_ALERT_ENABLED", "False").lower() == "true",
        "bot_token": os.getenv("TELEGRAM_BOT_TOKEN", ""),
        "chat_ids": os.getenv("TELEGRAM_CHAT_IDS", "").split(",")
    },
    
    # 日志文件告警配置
    "log_file": {
        "enabled": True,
        "path": os.getenv("ALERT_LOG_FILE", "logs/alerts.log")
    }
}

# Web服务器配置
WEB_CONFIG = {
    "host": os.getenv("WEB_HOST", "0.0.0.0"),
    "port": int(os.getenv("WEB_PORT", "5000")),
    "debug": os.getenv("WEB_DEBUG", "False").lower() == "true",
    "cors_origins": os.getenv("CORS_ORIGINS", "*").split(","),
    
    # WebSocket配置
    "websocket_port": int(os.getenv("WEBSOCKET_PORT", "5001")),
    
    # 用户配置（实际应用中应使用数据库存储）
    "users": {
        "admin": {
            "id": "admin001",
            "password_hash": os.getenv("ADMIN_PASSWORD_HASH", ""),  # 使用werkzeug.security.generate_password_hash生成
            "role": "admin",
            "display_name": "管理员"
        },
        "user": {
            "id": "user001",
            "password_hash": os.getenv("USER_PASSWORD_HASH", ""),
            "role": "user",
            "display_name": "普通用户"
        }
    }
}

# JWT配置
JWT_CONFIG = {
    "secret_key": os.getenv("JWT_SECRET_KEY", "default_secret_key"),
    "expiration_hours": int(os.getenv("JWT_EXPIRATION_HOURS", "24")),
    "algorithm": "HS256"
}

# 检查必要的环境变量
def check_required_env_vars():
    """检查必要的环境变量是否已设置"""
    required_vars = [
        "OPENAI_API_KEY",
        "INFLUXDB_TOKEN"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"警告：以下必要的环境变量未设置: {', '.join(missing_vars)}")
        return False
    
    return True 
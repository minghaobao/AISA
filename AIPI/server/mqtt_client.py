import paho.mqtt.client as mqtt
import json
import time
import logging
from config import MQTT_CONFIG, LOG_CONFIG
from langchain_processor import process_device_data

# 配置日志
logging.basicConfig(
    level=LOG_CONFIG["level"],
    format=LOG_CONFIG["format"],
    filename=LOG_CONFIG.get("filename")
)
logger = logging.getLogger("mqtt_client")

class MQTTClient:
    def __init__(self):
        self.client = mqtt.Client()
        self.client.username_pw_set(
            MQTT_CONFIG["username"], 
            MQTT_CONFIG["password"]
        )
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.connected = False
        
    def connect(self):
        """连接到MQTT代理服务器"""
        try:
            self.client.connect(
                MQTT_CONFIG["broker_host"],
                MQTT_CONFIG["broker_port"],
                MQTT_CONFIG["keep_alive"]
            )
            self.client.loop_start()
            logger.info("MQTT客户端启动成功")
            return True
        except Exception as e:
            logger.error(f"MQTT连接失败: {str(e)}")
            return False
            
    def on_connect(self, client, userdata, flags, rc):
        """连接回调函数"""
        if rc == 0:
            logger.info("已连接到MQTT代理服务器")
            self.connected = True
            # 订阅设备数据主题
            for topic in MQTT_CONFIG["subscribe_topics"]:
                self.client.subscribe(topic)
                logger.info(f"已订阅主题: {topic}")
        else:
            logger.error(f"连接MQTT代理服务器失败，返回码: {rc}")
            
    def on_message(self, client, userdata, msg):
        """消息接收回调函数"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            logger.debug(f"收到消息，主题: {topic}，内容: {payload}")
            
            # 解析JSON数据
            try:
                data = json.loads(payload)
                # 将消息传递给LangChain处理器进行处理
                process_device_data(topic, data)
            except json.JSONDecodeError:
                logger.warning(f"无法解析JSON数据: {payload}")
                
        except Exception as e:
            logger.error(f"处理消息时出错: {str(e)}")
            
    def on_disconnect(self, client, userdata, rc):
        """断开连接回调函数"""
        self.connected = False
        if rc != 0:
            logger.warning(f"意外断开MQTT连接，返回码: {rc}")
            # 尝试重新连接
            time.sleep(5)
            self.connect()
        else:
            logger.info("已断开MQTT连接")
            
    def publish(self, topic, message):
        """发布消息到指定主题"""
        try:
            if isinstance(message, dict):
                message = json.dumps(message)
                
            result = self.client.publish(topic, message)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.debug(f"消息发布成功 - 主题: {topic}, 消息: {message}")
                return True
            else:
                logger.error(f"消息发布失败 - 错误码: {result.rc}")
                return False
        except Exception as e:
            logger.error(f"发布消息时出错: {str(e)}")
            return False
            
    def disconnect(self):
        """断开MQTT连接"""
        self.client.loop_stop()
        self.client.disconnect()
        logger.info("MQTT客户端已停止")

# 单例模式实现
mqtt_client = MQTTClient()

def get_mqtt_client():
    """获取MQTT客户端单例"""
    return mqtt_client

if __name__ == "__main__":
    # 测试代码
    client = get_mqtt_client()
    client.connect()
    
    # 发布测试消息
    test_message = {
        "device_id": "test_device",
        "temperature": 25.5,
        "humidity": 60,
        "timestamp": time.time()
    }
    client.publish(MQTT_CONFIG["publish_topics"]["device_control"], test_message)
    
    try:
        # 保持程序运行
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        client.disconnect() 
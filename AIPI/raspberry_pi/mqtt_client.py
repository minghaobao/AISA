import paho.mqtt.client as mqtt
import json
import time
import logging
import threading
import os
import psutil
import platform

# 使用本地配置
from config import MQTT_CONFIG, LOG_CONFIG, DEVICE_ID, DATA_COLLECTION_CONFIG

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
        
        # 存储当前正在执行的命令
        self.active_commands = {}
        
        # 数据收集线程
        self.data_collection_thread = None
        self.stop_collection = False
        
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
            
            # 订阅命令主题
            for topic in MQTT_CONFIG["subscribe_topics"]:
                self.client.subscribe(topic)
                logger.info(f"已订阅主题: {topic}")
                
            # 发布设备上线状态
            self.publish_device_status("online")
            
            # 启动数据收集线程
            self.start_data_collection()
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
                
                # 处理命令
                if topic.endswith("/command"):
                    self.handle_command(data)
                    
                # 处理设备控制
                elif "device/control" in topic:
                    self.handle_device_control(topic, data)
                    
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
            # 停止数据收集
            self.stop_collection = True
            
    def publish(self, topic, message):
        """发布消息到指定主题"""
        try:
            if isinstance(message, dict):
                message = json.dumps(message, ensure_ascii=False)
                
            result = self.client.publish(topic, message)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.debug(f"消息发布成功 - 主题: {topic}")
                return True
            else:
                logger.error(f"消息发布失败 - 错误码: {result.rc}")
                return False
        except Exception as e:
            logger.error(f"发布消息时出错: {str(e)}")
            return False
            
    def publish_device_status(self, status):
        """发布设备状态"""
        device_status = {
            "device_id": DEVICE_ID,
            "status": status,
            "timestamp": time.time(),
            "ip_address": self.get_ip_address(),
            "hostname": platform.node()
        }
        
        return self.publish(
            MQTT_CONFIG["publish_topics"]["device_status"], 
            device_status
        )
        
    def publish_device_data(self):
        """发布设备数据"""
        try:
            data = self.collect_device_data()
            data["device_id"] = DEVICE_ID
            data["timestamp"] = time.time()
            
            return self.publish(
                MQTT_CONFIG["publish_topics"]["device_data"], 
                data
            )
        except Exception as e:
            logger.error(f"发布设备数据时出错: {str(e)}")
            return False
            
    def publish_command_result(self, command_id, success, output="", error=""):
        """发布命令执行结果"""
        result = {
            "device_id": DEVICE_ID,
            "command_id": command_id,
            "success": success,
            "output": output,
            "error": error,
            "timestamp": time.time()
        }
        
        return self.publish(
            MQTT_CONFIG["publish_topics"]["command_result"], 
            result
        )
    
    def collect_device_data(self):
        """收集设备数据"""
        data = {}
        
        # 根据配置决定收集哪些数据
        if DATA_COLLECTION_CONFIG["collect_cpu"]:
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_freq = psutil.cpu_freq()
            data["cpu_usage"] = cpu_percent
            if cpu_freq:
                data["cpu_freq"] = cpu_freq.current
                
        if DATA_COLLECTION_CONFIG["collect_memory"]:
            memory = psutil.virtual_memory()
            data["memory_total"] = memory.total
            data["memory_used"] = memory.used
            data["memory_percent"] = memory.percent
            
        if DATA_COLLECTION_CONFIG["collect_disk"]:
            disk = psutil.disk_usage('/')
            data["disk_total"] = disk.total
            data["disk_used"] = disk.used
            data["disk_percent"] = disk.percent
            
        if DATA_COLLECTION_CONFIG["collect_network"]:
            net_io = psutil.net_io_counters()
            data["net_bytes_sent"] = net_io.bytes_sent
            data["net_bytes_recv"] = net_io.bytes_recv
            
        if DATA_COLLECTION_CONFIG["collect_temperature"]:
            # 尝试获取CPU温度
            temp = self.get_cpu_temperature()
            if temp:
                data["cpu_temperature"] = temp
                
        # 添加开机时间
        data["boot_time"] = psutil.boot_time()
        data["uptime_seconds"] = time.time() - psutil.boot_time()
        
        return data
        
    def get_cpu_temperature(self):
        """获取CPU温度，仅在树莓派上有效"""
        try:
            # 针对树莓派的温度读取
            if os.path.isfile('/sys/class/thermal/thermal_zone0/temp'):
                with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                    temp = float(f.read()) / 1000.0
                return temp
        except Exception as e:
            logger.debug(f"获取CPU温度出错: {str(e)}")
        return None
        
    def get_ip_address(self):
        """获取设备IP地址"""
        try:
            # 只获取第一个非回环接口的地址
            for interface, addrs in psutil.net_if_addrs().items():
                if interface != 'lo':
                    for addr in addrs:
                        if addr.family == 2:  # AF_INET
                            return addr.address
        except Exception as e:
            logger.error(f"获取IP地址出错: {str(e)}")
        return "unknown"
    
    def handle_command(self, data):
        """处理收到的命令"""
        from command_executor import execute_command
        
        command_id = data.get("command_id")
        command = data.get("command")
        timeout = data.get("timeout", 30)
        
        if not command_id or not command:
            logger.warning("收到无效命令格式")
            return
            
        logger.info(f"收到命令: [{command}], ID: {command_id}")
        
        # 在新线程中执行命令
        def run_command():
            try:
                # 记录活动命令
                self.active_commands[command_id] = command
                
                # 执行命令
                success, output, error = execute_command(command, timeout)
                
                # 发布结果
                self.publish_command_result(command_id, success, output, error)
                
            except Exception as e:
                logger.error(f"执行命令出错: {str(e)}")
                self.publish_command_result(
                    command_id, False, 
                    error=f"执行出错: {str(e)}"
                )
            finally:
                # 移除活动命令
                if command_id in self.active_commands:
                    del self.active_commands[command_id]
        
        # 启动执行线程
        thread = threading.Thread(target=run_command)
        thread.daemon = True
        thread.start()
    
    def handle_device_control(self, topic, data):
        """处理设备控制消息"""
        from device_controller import execute_device_action
        
        try:
            device_id = data.get("device_id")
            action = data.get("action")
            parameters = data.get("parameters", {})
            
            if not device_id or not action:
                logger.warning("收到无效设备控制消息格式")
                return
                
            logger.info(f"收到设备控制: 设备={device_id}, 动作={action}")
            
            # 执行设备控制
            result = execute_device_action(device_id, action, parameters)
            
            # 发布控制结果
            self.publish(
                MQTT_CONFIG["publish_topics"]["device_status"],
                {
                    "device_id": DEVICE_ID,
                    "control_result": result,
                    "timestamp": time.time()
                }
            )
            
        except Exception as e:
            logger.error(f"处理设备控制时出错: {str(e)}")
    
    def start_data_collection(self):
        """启动数据收集线程"""
        def collection_thread():
            logger.info("设备数据收集线程已启动")
            interval = DATA_COLLECTION_CONFIG["interval_seconds"]
            
            while not self.stop_collection:
                try:
                    # 发布设备数据
                    self.publish_device_data()
                except Exception as e:
                    logger.error(f"数据收集出错: {str(e)}")
                
                # 休眠指定间隔时间
                for _ in range(interval):
                    if self.stop_collection:
                        break
                    time.sleep(1)
        
        self.stop_collection = False
        self.data_collection_thread = threading.Thread(target=collection_thread)
        self.data_collection_thread.daemon = True
        self.data_collection_thread.start()
            
    def disconnect(self):
        """断开MQTT连接"""
        # 发布离线状态
        self.publish_device_status("offline")
        
        # 停止数据收集
        self.stop_collection = True
        if self.data_collection_thread:
            self.data_collection_thread.join(timeout=5)
            
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
    
    try:
        # 保持程序运行
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        client.disconnect() 
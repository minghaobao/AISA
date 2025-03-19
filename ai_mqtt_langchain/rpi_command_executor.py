#!/usr/bin/env python3
import os
import time
import json
import logging
import argparse
import subprocess
from datetime import datetime
import paho.mqtt.client as mqtt
import platform

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='rpi_executor.log',
)
logger = logging.getLogger("rpi_executor")

# 创建控制台处理器
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console.setFormatter(formatter)
logger.addHandler(console)

class CommandExecutor:
    def __init__(self, config):
        self.config = config
        self.device_id = config['device_id']
        self.mqtt_client = None
        self.connected = False
        
        # 命令执行结果存储
        self.command_results = {}
        
        # 创建MQTT客户端
        self.setup_mqtt()
    
    def setup_mqtt(self):
        """设置MQTT客户端"""
        client_id = f"{self.device_id}_{int(time.time())}"
        self.mqtt_client = mqtt.Client(client_id=client_id)
        
        # 设置回调函数
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.on_disconnect = self.on_disconnect
        
        # 设置认证信息
        if self.config.get('mqtt_username') and self.config.get('mqtt_password'):
            self.mqtt_client.username_pw_set(
                self.config['mqtt_username'], 
                self.config['mqtt_password']
            )
    
    def connect(self):
        """连接到MQTT代理服务器"""
        try:
            logger.info(f"正在连接到MQTT代理服务器 {self.config['mqtt_host']}:{self.config['mqtt_port']}...")
            self.mqtt_client.connect(
                self.config['mqtt_host'], 
                self.config['mqtt_port'],
                keepalive=60
            )
            self.mqtt_client.loop_start()
            return True
        except Exception as e:
            logger.error(f"连接MQTT代理服务器失败: {e}")
            return False
    
    def on_connect(self, client, userdata, flags, rc):
        """连接回调函数"""
        if rc == 0:
            self.connected = True
            logger.info("已连接到MQTT代理服务器")
            
            # 订阅命令主题
            command_topic = f"device/{self.device_id}/command"
            self.mqtt_client.subscribe(command_topic)
            logger.info(f"已订阅命令主题: {command_topic}")
            
            # 发送上线消息
            self.publish_status("online")
        else:
            logger.error(f"连接MQTT代理服务器失败，返回码: {rc}")
    
    def on_disconnect(self, client, userdata, rc):
        """断开连接回调函数"""
        self.connected = False
        logger.warning(f"与MQTT代理服务器断开连接，返回码: {rc}")
        
        # 尝试重新连接
        if rc != 0:
            logger.info("尝试重新连接...")
            time.sleep(5)
            self.connect()
    
    def on_message(self, client, userdata, msg):
        """消息回调函数"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            logger.debug(f"收到消息: {topic} => {payload}")
            
            # 处理命令主题消息
            if topic == f"device/{self.device_id}/command":
                self.handle_command(payload)
                
        except Exception as e:
            logger.error(f"处理消息时出错: {e}")
    
    def handle_command(self, payload):
        """处理命令消息"""
        try:
            # 解析命令消息
            data = json.loads(payload)
            command_id = data.get('command_id', str(int(time.time())))
            command = data.get('command')
            timeout = data.get('timeout', 60)
            
            if not command:
                logger.warning("收到无效命令消息，缺少command字段")
                self.publish_result(command_id, False, "无效命令，缺少command字段")
                return
                
            logger.info(f"执行命令 [{command_id}]: {command}")
            
            # 执行命令
            result = self.execute_command(command, timeout)
            
            # 发布执行结果
            self.publish_result(command_id, result['success'], result['output'], result.get('error'))
                
        except json.JSONDecodeError:
            logger.warning(f"无法解析命令消息为JSON: {payload}")
            self.publish_result('unknown', False, "无法解析命令消息为JSON")
        except Exception as e:
            logger.error(f"处理命令时出错: {e}")
            self.publish_result('unknown', False, f"处理命令时出错: {str(e)}")
    
    def execute_command(self, command, timeout=60):
        """
        执行shell命令
        :param command: 要执行的命令
        :param timeout: 命令超时时间（秒）
        :return: 包含执行结果的字典
        """
        try:
            # 执行命令并捕获输出
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            try:
                stdout, stderr = process.communicate(timeout=timeout)
                return {
                    'success': process.returncode == 0,
                    'return_code': process.returncode,
                    'output': stdout,
                    'error': stderr,
                    'timestamp': datetime.now().isoformat()
                }
            except subprocess.TimeoutExpired:
                process.kill()
                return {
                    'success': False,
                    'output': '',
                    'error': f'命令执行超时 (>{timeout}秒)',
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            return {
                'success': False,
                'output': '',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def publish_result(self, command_id, success, output, error=None):
        """
        发布命令执行结果
        :param command_id: 命令ID
        :param success: 是否成功
        :param output: 输出内容
        :param error: 错误内容
        """
        result = {
            'device_id': self.device_id,
            'command_id': command_id,
            'success': success,
            'output': output,
            'timestamp': datetime.now().isoformat()
        }
        
        if error:
            result['error'] = error
        
        # 存储结果
        self.command_results[command_id] = result
        
        # 发布结果
        result_topic = f"device/{self.device_id}/result"
        self.mqtt_client.publish(result_topic, json.dumps(result))
        logger.info(f"已发布命令 [{command_id}] 执行结果")
    
    def publish_status(self, status):
        """
        发布设备状态
        :param status: 状态字符串
        """
        status_data = {
            'device_id': self.device_id,
            'status': status,
            'timestamp': datetime.now().isoformat()
        }
        
        status_topic = f"device/{self.device_id}/status"
        self.mqtt_client.publish(status_topic, json.dumps(status_data))
        logger.info(f"已发布设备状态: {status}")
    
    def publish_heartbeat(self):
        """发布心跳消息"""
        heartbeat_data = {
            'device_id': self.device_id,
            'timestamp': datetime.now().isoformat(),
            'uptime': self.get_uptime(),
            'memory_usage': self.get_memory_usage(),
            'cpu_temperature': self.get_cpu_temperature()
        }
        
        heartbeat_topic = f"device/{self.device_id}/heartbeat"
        self.mqtt_client.publish(heartbeat_topic, json.dumps(heartbeat_data))
        logger.debug("已发布心跳消息")
    
    def get_uptime(self):
        """获取系统运行时间"""
        try:
            import platform
            system = platform.system()
            
            # 尝试使用psutil（跨平台方法）
            try:
                import psutil
                return psutil.boot_time()
            except ImportError:
                logger.warning("无法导入psutil模块，尝试使用系统特定方法")
                
                # Linux特定方法
                if system == "Linux":
                    with open('/proc/uptime', 'r') as f:
                        uptime_seconds = float(f.readline().split()[0])
                        return uptime_seconds
                # Windows特定方法
                elif system == "Windows":
                    try:
                        import subprocess
                        output = subprocess.check_output('net statistics server', shell=True).decode()
                        for line in output.splitlines():
                            if "Statistics since" in line:
                                import datetime
                                import time
                                # 解析日期和时间
                                date_str = line.split("Statistics since")[1].strip()
                                start_time = datetime.datetime.strptime(date_str, "%d/%m/%Y %H:%M:%S")
                                now = datetime.datetime.now()
                                return (now - start_time).total_seconds()
                    except Exception as e:
                        logger.warning(f"无法获取Windows启动时间: {e}")
        except Exception as e:
            logger.warning(f"获取系统运行时间时出错: {e}")
        
        return 0
    
    def get_memory_usage(self):
        """获取内存使用情况"""
        try:
            import platform
            system = platform.system()
            
            # 尝试使用psutil（跨平台方法）
            try:
                import psutil
                memory = psutil.virtual_memory()
                return {
                    'total': int(memory.total / (1024 * 1024)),  # 转换为MB
                    'used': int(memory.used / (1024 * 1024)),    # 转换为MB
                    'percentage': memory.percent
                }
            except ImportError:
                logger.warning("无法导入psutil模块，尝试使用系统命令获取内存信息")
                
                # 在Linux上使用free命令
                if system == "Linux":
                    result = self.execute_command('free -m | grep Mem')
                    if result['success']:
                        parts = result['output'].split()
                        total = int(parts[1])
                        used = int(parts[2])
                        return {
                            'total': total,
                            'used': used,
                            'percentage': round(used / total * 100, 2)
                        }
        except Exception as e:
            logger.warning(f"获取内存使用情况时出错: {e}")
        
        # 如果以上方法都失败，返回默认值
        return {
            'total': 0,
            'used': 0,
            'percentage': 0
        }
    
    def get_cpu_temperature(self):
        """获取CPU温度"""
        try:
            import platform
            
            # 检查操作系统类型
            system = platform.system()
            
            if system == "Linux":
                # 适用于树莓派和大多数Linux系统
                if os.path.exists('/sys/class/thermal/thermal_zone0/temp'):
                    with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                        temp = float(f.read()) / 1000.0
                        return temp
                        
            elif system == "Windows":
                # 在Windows上尝试使用wmi获取温度信息
                try:
                    import wmi
                    w = wmi.WMI(namespace="root\wmi")
                    temperature_info = w.MSAcpi_ThermalZoneTemperature()[0]
                    # 转换为摄氏度
                    temp = (float(temperature_info.CurrentTemperature) / 10.0) - 273.15
                    return temp
                except ImportError:
                    logger.warning("无法导入wmi模块，无法获取Windows CPU温度")
                    return 0
                except Exception as e:
                    logger.warning(f"获取Windows CPU温度失败: {e}")
                    return 0
                    
            # 对于不支持的系统或获取失败，尝试使用psutil
            try:
                import psutil
                temperatures = psutil.sensors_temperatures()
                if temperatures:
                    for name, entries in temperatures.items():
                        for entry in entries:
                            return entry.current
                return 0
            except Exception:
                pass
            
        except Exception as e:
            logger.warning(f"获取CPU温度时出错: {e}")
        
        return 0
    
    def run(self):
        """运行命令执行器"""
        if not self.connect():
            logger.error("无法连接到MQTT代理服务器，程序退出")
            return False
        
        # 发送上线状态
        self.publish_status("online")
        
        # 主循环
        heartbeat_interval = self.config.get('heartbeat_interval', 60)
        last_heartbeat = 0
        
        try:
            while True:
                # 检查是否需要发送心跳
                current_time = time.time()
                if current_time - last_heartbeat >= heartbeat_interval:
                    self.publish_heartbeat()
                    last_heartbeat = current_time
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("接收到退出信号")
        finally:
            # 发布离线状态
            self.publish_status("offline")
            # 停止MQTT客户端
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            logger.info("程序已退出")
        
        return True

def load_config(config_file=None):
    """
    加载配置
    :param config_file: 配置文件路径
    :return: 配置字典
    """
    # 默认配置
    config = {
        'device_id': f"rpi_{platform.node()}",
        'mqtt_host': 'localhost',
        'mqtt_port': 1883,
        'mqtt_username': '',
        'mqtt_password': '',
        'heartbeat_interval': 60
    }
    
    # 从配置文件加载
    if config_file and os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                file_config = json.load(f)
                config.update(file_config)
                logger.info(f"已从 {config_file} 加载配置")
        except Exception as e:
            logger.error(f"加载配置文件时出错: {e}")
    
    # 从环境变量加载
    for key in config:
        env_key = f"RPI_EXECUTOR_{key.upper()}"
        if env_key in os.environ:
            config[key] = os.environ[env_key]
    
    return config

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="树莓派命令执行器")
    parser.add_argument("--config", help="配置文件路径", default="rpi_executor_config.json")
    parser.add_argument("--device-id", help="设备ID")
    parser.add_argument("--mqtt-host", help="MQTT代理服务器主机")
    parser.add_argument("--mqtt-port", type=int, help="MQTT代理服务器端口")
    parser.add_argument("--mqtt-username", help="MQTT用户名")
    parser.add_argument("--mqtt-password", help="MQTT密码")
    parser.add_argument("--heartbeat-interval", type=int, help="心跳间隔（秒）")
    
    args = parser.parse_args()
    
    # 加载配置
    config = load_config(args.config)
    
    # 更新命令行参数
    for arg_name, arg_value in vars(args).items():
        if arg_value is not None and arg_name != 'config':
            config[arg_name.replace('-', '_')] = arg_value
    
    # 打印配置信息
    logger.info(f"设备ID: {config['device_id']}")
    logger.info(f"MQTT代理服务器: {config['mqtt_host']}:{config['mqtt_port']}")
    
    # 创建并运行执行器
    executor = CommandExecutor(config)
    executor.run() 
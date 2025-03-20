"""
数据管理模块 - 负责数据写入InfluxDB和数据查询
"""
import os
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS, ASYNCHRONOUS
import json

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("data_manager")

# 加载环境变量
load_dotenv()

class DataManager:
    """数据管理器类，处理InfluxDB数据写入和查询"""
    
    def __init__(self, url=None, token=None, org=None, bucket=None, devices_file=None):
        """初始化数据管理器"""
        self.influx_url = url or os.environ.get("INFLUXDB_URL", "http://localhost:8086")
        self.influx_token = token or os.environ.get("INFLUXDB_TOKEN", "your-token")
        self.influx_org = org or os.environ.get("INFLUXDB_ORG", "your-org")
        self.influx_bucket = bucket or os.environ.get("INFLUXDB_BUCKET", "iot_data")
        
        self.client = None
        self.write_api = None
        self.query_api = None
        
        # 设备信息文件
        self.devices_file = devices_file or os.environ.get("DEVICES_FILE", "devices.json")
        
        # 设备信息缓存
        self._devices_cache = None
        self._last_devices_read = 0
        
        # 确保设备文件存在
        self._ensure_devices_file()
    
    def _ensure_devices_file(self):
        """确保设备文件存在"""
        if not os.path.isfile(self.devices_file):
            # 创建基础文件，使用项目根目录下的devices.json
            if not os.path.isabs(self.devices_file):
                # 如果是相对路径，则使用项目根目录
                current_dir = os.path.dirname(os.path.abspath(__file__))
                self.devices_file = os.path.join(current_dir, self.devices_file)
            
            # 创建包含基本结构的设备文件
            with open(self.devices_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "devices": [],
                    "last_updated": datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
            
            logger.info(f"已创建设备信息文件: {self.devices_file}")
    
    def _connect(self) -> bool:
        """连接到InfluxDB"""
        try:
            if self.client is None:
                self.client = InfluxDBClient(
                    url=self.influx_url,
                    token=self.influx_token,
                    org=self.influx_org
                )
                self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
                self.query_api = self.client.query_api()
                
                # 检查连接
                health = self.client.health()
                if health.status == "pass":
                    logger.info("成功连接到InfluxDB")
                    return True
                else:
                    logger.warning(f"InfluxDB健康检查失败: {health.message}")
                    return False
            
            # 如果已有客户端，检查是否可用
            health = self.client.health()
            return health.status == "pass"
        
        except Exception as e:
            logger.error(f"连接InfluxDB时出错: {e}")
            self.client = None
            self.write_api = None
            self.query_api = None
            return False
    
    def write_point(self, point: Point) -> bool:
        """写入一个数据点"""
        if not self._connect():
            logger.error("无法连接到InfluxDB，无法写入数据")
            return False
        
        try:
            self.write_api.write(bucket=self.influx_bucket, record=point)
            return True
        except Exception as e:
            logger.error(f"写入数据点时出错: {e}")
            return False
    
    def write_device_data(self, device_id: str, data: Dict[str, Any]) -> bool:
        """写入设备数据"""
        if not data:
            logger.warning("没有数据可写入")
            return False
        
        try:
            # 创建数据点
            point = Point("device_data")
            point = point.tag("device_id", device_id)
            point = point.time(time.time_ns())
            
            # 添加所有字段
            for key, value in data.items():
                if isinstance(value, (int, float)):
                    point = point.field(key, value)
                else:
                    # 非数值类型转为字符串
                    point = point.field(key, str(value))
            
            # 写入数据
            return self.write_point(point)
        
        except Exception as e:
            logger.error(f"准备设备数据时出错: {e}")
            return False
    
    def write_command_result(self, device_id: str, command: str, success: bool, 
                            output: str = "", error: str = "") -> bool:
        """写入命令执行结果"""
        try:
            # 创建数据点
            point = Point("command_results")
            point = point.tag("device_id", device_id)
            point = point.time(time.time_ns())
            
            # 添加字段
            point = point.field("command", command)
            point = point.field("success", success)
            point = point.field("output", output)
            point = point.field("error", error)
            
            # 写入数据
            return self.write_point(point)
        
        except Exception as e:
            logger.error(f"准备命令结果数据时出错: {e}")
            return False
    
    def write_alert(self, device_id: str, alert_type: str, message: str, 
                   severity: str = "info", data: Dict[str, Any] = None) -> bool:
        """写入告警数据"""
        try:
            # 创建数据点
            point = Point("alerts")
            point = point.tag("device_id", device_id)
            point = point.time(time.time_ns())
            
            # 添加基本字段
            point = point.field("alert_type", alert_type)
            point = point.field("message", message)
            point = point.field("severity", severity)
            
            # 添加额外数据
            if data:
                for key, value in data.items():
                    if isinstance(value, (int, float, bool, str)):
                        point = point.field(f"data_{key}", value)
                    else:
                        # 其他类型转换为JSON
                        json_value = json.dumps(value, ensure_ascii=False)
                        point = point.field(f"data_{key}", json_value)
            
            # 写入数据
            success = self.write_point(point)
            
            if success:
                # 更新设备状态
                device = self.get_device(device_id)
                if device:
                    # 更新设备上次告警字段
                    device["last_alert"] = {
                        "time": datetime.now().isoformat(),
                        "type": alert_type,
                        "message": message,
                        "severity": severity
                    }
                    self.update_device(device_id, device)
            
            return success
        
        except Exception as e:
            logger.error(f"准备告警数据时出错: {e}")
            return False
    
    def query_device_data(self, device_id: str, measurement: str = "device_data", 
                         start_time: str = "-1h", limit: int = 100) -> List[Dict[str, Any]]:
        """查询设备数据
        
        Args:
            device_id: 设备ID
            measurement: 测量类型 (device_data, command_results, alerts)
            start_time: 开始时间 (如 -1h, -1d, 2023-01-01T00:00:00Z)
            limit: 返回结果数量限制
            
        Returns:
            数据列表
        """
        if not self._connect():
            logger.error("无法连接到InfluxDB，无法查询数据")
            return []
        
        try:
            # 构建Flux查询
            query = f'''
            from(bucket: "{self.influx_bucket}")
                |> range(start: {start_time})
                |> filter(fn: (r) => r["_measurement"] == "{measurement}")
                |> filter(fn: (r) => r["device_id"] == "{device_id}")
                |> limit(n: {limit})
            '''
            
            # 执行查询
            tables = self.query_api.query(query)
            
            # 处理结果
            results = []
            for table in tables:
                for record in table.records:
                    results.append({
                        "time": record.get_time().isoformat(),
                        "field": record.get_field(),
                        "value": record.get_value(),
                        "device_id": record.values.get("device_id", "")
                    })
            
            return results
        
        except Exception as e:
            logger.error(f"查询设备数据时出错: {e}")
            return []
    
    def load_devices(self, force_reload: bool = False) -> List[Dict[str, Any]]:
        """加载所有设备信息
        
        Args:
            force_reload: 是否强制从文件重新加载，忽略缓存
            
        Returns:
            设备信息列表
        """
        # 如果缓存存在且未超过5分钟，直接返回缓存
        current_time = time.time()
        if not force_reload and self._devices_cache and (current_time - self._last_devices_read < 300):
            return self._devices_cache
        
        try:
            if not os.path.isfile(self.devices_file):
                self._ensure_devices_file()
                return []
            
            with open(self.devices_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                devices = data.get("devices", [])
                
                # 更新缓存
                self._devices_cache = devices
                self._last_devices_read = current_time
                
                return devices
        
        except Exception as e:
            logger.error(f"加载设备信息时出错: {e}")
            return []
    
    def save_devices(self, devices: List[Dict[str, Any]]) -> bool:
        """保存所有设备信息
        
        Args:
            devices: 设备信息列表
            
        Returns:
            是否保存成功
        """
        try:
            # 准备数据
            data = {
                "devices": devices,
                "last_updated": datetime.now().isoformat()
            }
            
            # 写入文件
            with open(self.devices_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # 更新缓存
            self._devices_cache = devices
            self._last_devices_read = time.time()
            
            return True
        
        except Exception as e:
            logger.error(f"保存设备信息时出错: {e}")
            return False
    
    def get_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        """获取单个设备信息
        
        Args:
            device_id: 设备ID
            
        Returns:
            设备信息，如果不存在则返回None
        """
        devices = self.load_devices()
        
        for device in devices:
            if device.get("device_id") == device_id:
                return device
        
        return None
    
    def add_device(self, device_data: Dict[str, Any]) -> bool:
        """添加新设备
        
        Args:
            device_data: 设备信息字典，必须包含device_id字段
            
        Returns:
            是否添加成功
        """
        if "device_id" not in device_data:
            logger.error("设备信息必须包含device_id字段")
            return False
        
        # 检查是否已存在
        device_id = device_data["device_id"]
        if self.get_device(device_id):
            logger.error(f"设备ID为{device_id}的设备已存在")
            return False
        
        # 添加设备注册时间
        if "registered_at" not in device_data:
            device_data["registered_at"] = datetime.now().isoformat()
        
        # 添加默认状态
        if "status" not in device_data:
            device_data["status"] = "registered"
        
        # 获取所有设备并添加新设备
        devices = self.load_devices()
        devices.append(device_data)
        
        # 保存
        return self.save_devices(devices)
    
    def update_device(self, device_id: str, device_data: Dict[str, Any]) -> bool:
        """更新设备信息
        
        Args:
            device_id: 设备ID
            device_data: 更新后的设备数据
            
        Returns:
            是否更新成功
        """
        # 获取所有设备
        devices = self.load_devices()
        
        # 查找设备并更新
        found = False
        for i, device in enumerate(devices):
            if device.get("device_id") == device_id:
                # 保留原始的device_id，不允许修改
                device_data["device_id"] = device_id
                
                # 添加更新时间
                device_data["updated_at"] = datetime.now().isoformat()
                
                # 保留注册时间
                if "registered_at" in device:
                    device_data["registered_at"] = device["registered_at"]
                
                # 更新设备
                devices[i] = device_data
                found = True
                break
        
        if not found:
            logger.error(f"未找到设备ID为{device_id}的设备")
            return False
        
        # 保存
        return self.save_devices(devices)
    
    def delete_device(self, device_id: str) -> bool:
        """删除设备
        
        Args:
            device_id: 设备ID
            
        Returns:
            是否删除成功
        """
        # 获取所有设备
        devices = self.load_devices()
        
        # 查找并删除设备
        found = False
        for i, device in enumerate(devices):
            if device.get("device_id") == device_id:
                devices.pop(i)
                found = True
                break
        
        if not found:
            logger.error(f"未找到设备ID为{device_id}的设备")
            return False
        
        # 保存
        return self.save_devices(devices)
    
    def get_device_status(self, device_id: str) -> Dict[str, Any]:
        """获取设备状态信息，包括最新数据和告警
        
        Args:
            device_id: 设备ID
            
        Returns:
            设备状态字典
        """
        # 获取设备信息
        device = self.get_device(device_id)
        if not device:
            return {"error": f"未找到设备ID为{device_id}的设备"}
        
        # 获取最新设备数据
        latest_data = self.query_device_data(
            device_id=device_id,
            measurement="device_data",
            start_time="-1h",
            limit=100
        )
        
        # 获取最新告警
        alerts = self.query_device_data(
            device_id=device_id,
            measurement="alerts",
            start_time="-24h",
            limit=5
        )
        
        # 整理数据结构
        status = {
            "device": device,
            "latest_data": latest_data,
            "alerts": alerts,
            "timestamp": datetime.now().isoformat()
        }
        
        return status
    
    def get_all_device_status(self) -> List[Dict[str, Any]]:
        """获取所有设备的状态概览
        
        Returns:
            所有设备状态列表
        """
        devices = self.load_devices()
        result = []
        
        for device in devices:
            device_id = device.get("device_id")
            if not device_id:
                continue
            
            # 查询设备最新数据
            try:
                latest_data = self.query_device_data(
                    device_id=device_id,
                    measurement="device_data",
                    start_time="-10m",  # 仅查询最近10分钟的数据
                    limit=10
                )
                
                # 提取主要数据点
                cpu_percent = None
                memory_percent = None
                disk_percent = None
                cpu_temp = None
                
                for item in latest_data:
                    if item.get("field") == "cpu_percent":
                        cpu_percent = item.get("value")
                    elif item.get("field") == "memory_percent":
                        memory_percent = item.get("value")
                    elif item.get("field") == "disk_percent":
                        disk_percent = item.get("value")
                    elif item.get("field") == "cpu_temp":
                        cpu_temp = item.get("value")
                
                # 计算最后活跃时间
                last_active = None
                if latest_data:
                    last_active = max([item.get("time") for item in latest_data])
                
                # 计算在线状态
                is_online = False
                if last_active:
                    last_active_time = datetime.fromisoformat(last_active.replace('Z', '+00:00'))
                    is_online = (datetime.now() - last_active_time) < timedelta(minutes=10)
                
                # 汇总状态信息
                status = {
                    "device_id": device_id,
                    "name": device.get("name", f"设备 {device_id}"),
                    "description": device.get("description", ""),
                    "status": "online" if is_online else "offline",
                    "last_active": last_active,
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory_percent,
                    "disk_percent": disk_percent,
                    "cpu_temp": cpu_temp,
                    "tags": device.get("tags", []),
                    "location": device.get("location", "")
                }
                
                result.append(status)
            
            except Exception as e:
                logger.error(f"获取设备{device_id}状态时出错: {e}")
                # 添加错误状态
                result.append({
                    "device_id": device_id,
                    "name": device.get("name", f"设备 {device_id}"),
                    "status": "error",
                    "error": str(e)
                })
        
        return result

# 全局数据管理器实例
_data_manager = None

def get_data_manager() -> DataManager:
    """获取数据管理器实例（单例模式）"""
    global _data_manager
    
    if _data_manager is None:
        _data_manager = DataManager()
    
    return _data_manager 
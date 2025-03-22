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

class DeviceManager:
    """设备管理器，负责设备的CRUD操作"""
    
    def __init__(self, data_path: str = None):
        """初始化设备管理器
        
        Args:
            data_path: 数据文件路径，默认为当前目录下的data/devices.json
        """
        if data_path is None:
            # 默认数据路径为当前目录下的data文件夹
            base_dir = os.path.dirname(os.path.abspath(__file__))
            self.data_path = os.path.join(base_dir, "data", "devices.json")
        else:
            self.data_path = data_path
            
        # 确保目录存在
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        
        # 加载设备数据
        self.devices = self._load_from_file()
        
    def _load_from_file(self) -> Dict[str, Any]:
        """从文件加载设备数据
        
        Returns:
            设备数据字典
        """
        try:
            if os.path.exists(self.data_path):
                with open(self.data_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # 文件不存在，返回空字典
                return {}
        except Exception as e:
            logger.error(f"加载设备数据出错: {e}")
            return {}
    
    def _save_to_file(self) -> bool:
        """保存设备数据到文件
        
        Returns:
            是否保存成功
        """
        try:
            with open(self.data_path, 'w', encoding='utf-8') as f:
                json.dump(self.devices, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存设备数据出错: {e}")
            return False
    
    def load_devices(self) -> List[Dict[str, Any]]:
        """获取所有设备列表
        
        Returns:
            设备列表
        """
        return [
            {**device_data, "device_id": device_id}
            for device_id, device_data in self.devices.items()
        ]
    
    def get_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        """获取指定设备信息
        
        Args:
            device_id: 设备ID
            
        Returns:
            设备信息，如果不存在则返回None
        """
        if device_id in self.devices:
            return {**self.devices[device_id], "device_id": device_id}
        return None
    
    def add_device(self, device_data: Dict[str, Any]) -> bool:
        """添加新设备
        
        Args:
            device_data: 设备数据，必须包含device_id字段
            
        Returns:
            是否添加成功
        """
        device_id = device_data.get("device_id")
        if not device_id:
            return False
        
        # 复制数据，移除device_id字段
        data_copy = device_data.copy()
        data_copy.pop("device_id", None)
        
        # 添加时间戳
        data_copy["created_at"] = datetime.now().isoformat()
        data_copy["updated_at"] = data_copy["created_at"]
        
        # 添加设备
        self.devices[device_id] = data_copy
        
        # 保存到文件
        return self._save_to_file()
    
    def update_device(self, device_id: str, device_data: Dict[str, Any]) -> bool:
        """更新设备信息
        
        Args:
            device_id: 设备ID
            device_data: 设备数据
            
        Returns:
            是否更新成功
        """
        if device_id not in self.devices:
            return False
        
        # 复制数据，移除device_id字段
        data_copy = device_data.copy()
        data_copy.pop("device_id", None)
        
        # 更新时间戳
        data_copy["updated_at"] = datetime.now().isoformat()
        
        # 保留创建时间
        if "created_at" in self.devices[device_id]:
            data_copy["created_at"] = self.devices[device_id]["created_at"]
        
        # 更新设备
        self.devices[device_id] = data_copy
        
        # 保存到文件
        return self._save_to_file()
    
    def delete_device(self, device_id: str) -> bool:
        """删除设备
        
        Args:
            device_id: 设备ID
            
        Returns:
            是否删除成功
        """
        if device_id not in self.devices:
            return False
        
        # 删除设备
        del self.devices[device_id]
        
        # 保存到文件
        return self._save_to_file()
    
    def get_all_device_status(self) -> List[Dict[str, Any]]:
        """获取所有设备状态
        
        Returns:
            设备状态列表
        """
        devices = self.load_devices()
        for device in devices:
            # 随机生成在线状态，真实环境应该查询设备实际状态
            device.setdefault("status", "offline")
            # 设置最后活跃时间
            device.setdefault("last_active", device.get("updated_at"))
        return devices
    
    def get_device_status(self, device_id: str) -> Dict[str, Any]:
        """获取单个设备状态
        
        Args:
            device_id: 设备ID
            
        Returns:
            设备状态
        """
        device = self.get_device(device_id)
        if not device:
            return {"error": f"未找到设备ID为{device_id}的设备"}
        
        # 随机生成在线状态，真实环境应该查询设备实际状态
        device.setdefault("status", "offline")
        # 设置最后活跃时间
        device.setdefault("last_active", device.get("updated_at"))
        
        return device

class DataManager:
    """数据管理器，整合设备管理、数据库存储等功能"""
    
    def __init__(self):
        """初始化数据管理器"""
        self.device_manager = DeviceManager()
    
    # 设备管理方法
    def load_devices(self) -> List[Dict[str, Any]]:
        return self.device_manager.load_devices()
    
    def get_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        return self.device_manager.get_device(device_id)
    
    def add_device(self, device_data: Dict[str, Any]) -> bool:
        return self.device_manager.add_device(device_data)
    
    def update_device(self, device_id: str, device_data: Dict[str, Any]) -> bool:
        return self.device_manager.update_device(device_id, device_data)
    
    def delete_device(self, device_id: str) -> bool:
        return self.device_manager.delete_device(device_id)
    
    def get_all_device_status(self) -> List[Dict[str, Any]]:
        return self.device_manager.get_all_device_status()
    
    def get_device_status(self, device_id: str) -> Dict[str, Any]:
        return self.device_manager.get_device_status(device_id)
    
    # 其他数据管理方法可以在这里添加
    def write_device_data(self, device_id: str, data: Dict[str, Any]) -> bool:
        """写入设备数据到数据库
        
        Args:
            device_id: 设备ID
            data: 设备数据
            
        Returns:
            是否写入成功
        """
        # 示例实现，真实环境应该写入到InfluxDB或其他数据库
        logger.info(f"写入设备数据: {device_id}, {data}")
        return True
    
    def write_command_result(self, device_id: str, command: str, success: bool, output: str = "", error: str = "") -> bool:
        """写入命令结果到数据库
        
        Args:
            device_id: 设备ID
            command: 命令
            success: 是否成功
            output: 输出
            error: 错误
            
        Returns:
            是否写入成功
        """
        # 示例实现，真实环境应该写入到InfluxDB或其他数据库
        logger.info(f"写入命令结果: {device_id}, {command}, {success}, {output}, {error}")
        return True

# 单例模式，确保只有一个数据管理器实例
_data_manager_instance = None

def get_data_manager() -> DataManager:
    """获取数据管理器实例
    
    Returns:
        数据管理器实例
    """
    global _data_manager_instance
    if _data_manager_instance is None:
        _data_manager_instance = DataManager()
    return _data_manager_instance 
from flask import Blueprint, jsonify, request
import os
import logging
import sys
from typing import Dict, List, Any, Optional
import json
from datetime import datetime

# 添加项目根目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# 导入数据管理器
try:
    from ai_mqtt_langchain.data_manager import get_data_manager
    data_manager = get_data_manager()
    data_manager_available = True
except ImportError as e:
    print(f"无法导入数据管理器: {e}")
    data_manager_available = False

# 创建Blueprint
devices_bp = Blueprint('devices', __name__, url_prefix='/api/devices')

# 日志配置
logger = logging.getLogger(__name__)

@devices_bp.route('/', methods=['GET'])
def get_devices():
    """获取所有设备列表"""
    if not data_manager_available:
        return jsonify({"error": "数据管理器不可用"}), 503
    
    try:
        # 参数
        show_status = request.args.get('status', 'false').lower() == 'true'
        tag_filter = request.args.get('tag')
        
        if show_status:
            # 获取所有设备状态
            devices = data_manager.get_all_device_status()
        else:
            # 只获取基本设备信息
            devices = data_manager.load_devices()
        
        # 过滤标签
        if tag_filter:
            filtered_devices = []
            for device in devices:
                device_tags = device.get('tags', [])
                if isinstance(device_tags, list) and tag_filter in device_tags:
                    filtered_devices.append(device)
                elif isinstance(device_tags, str) and tag_filter == device_tags:
                    filtered_devices.append(device)
            devices = filtered_devices
        
        return jsonify({
            "count": len(devices),
            "devices": devices
        })
    except Exception as e:
        logger.error(f"获取设备列表出错: {e}")
        return jsonify({"error": str(e)}), 500

@devices_bp.route('/<device_id>', methods=['GET'])
def get_device(device_id):
    """获取单个设备详细信息"""
    if not data_manager_available:
        return jsonify({"error": "数据管理器不可用"}), 503
    
    try:
        # 参数
        show_status = request.args.get('status', 'true').lower() == 'true'
        
        if show_status:
            # 获取设备状态
            device_data = data_manager.get_device_status(device_id)
            if "error" in device_data:
                return jsonify({"error": device_data["error"]}), 404
        else:
            # 只获取基本设备信息
            device_data = data_manager.get_device(device_id)
            if not device_data:
                return jsonify({"error": f"未找到设备ID为{device_id}的设备"}), 404
        
        return jsonify(device_data)
    except Exception as e:
        logger.error(f"获取设备{device_id}信息出错: {e}")
        return jsonify({"error": str(e)}), 500

@devices_bp.route('/', methods=['POST'])
def add_device():
    """添加新设备"""
    if not data_manager_available:
        return jsonify({"error": "数据管理器不可用"}), 503
    
    try:
        # 获取请求数据
        data = request.get_json()
        if not data:
            return jsonify({"error": "缺少设备数据"}), 400
        
        # 检查必需字段
        if "device_id" not in data:
            return jsonify({"error": "缺少必需的device_id字段"}), 400
        
        # 添加设备
        success = data_manager.add_device(data)
        
        if success:
            return jsonify({
                "success": True,
                "message": f"成功添加设备: {data['device_id']}",
                "device": data
            }), 201
        else:
            return jsonify({
                "success": False,
                "error": "添加设备失败"
            }), 500
    except Exception as e:
        logger.error(f"添加设备出错: {e}")
        return jsonify({"error": str(e)}), 500

@devices_bp.route('/<device_id>', methods=['PUT'])
def update_device(device_id):
    """更新设备信息"""
    if not data_manager_available:
        return jsonify({"error": "数据管理器不可用"}), 503
    
    try:
        # 获取请求数据
        data = request.get_json()
        if not data:
            return jsonify({"error": "缺少设备数据"}), 400
        
        # 检查设备是否存在
        existing_device = data_manager.get_device(device_id)
        if not existing_device:
            return jsonify({"error": f"未找到设备ID为{device_id}的设备"}), 404
        
        # 更新设备
        success = data_manager.update_device(device_id, data)
        
        if success:
            return jsonify({
                "success": True,
                "message": f"成功更新设备: {device_id}",
                "device": data
            })
        else:
            return jsonify({
                "success": False,
                "error": "更新设备失败"
            }), 500
    except Exception as e:
        logger.error(f"更新设备{device_id}出错: {e}")
        return jsonify({"error": str(e)}), 500

@devices_bp.route('/<device_id>', methods=['DELETE'])
def delete_device(device_id):
    """删除设备"""
    if not data_manager_available:
        return jsonify({"error": "数据管理器不可用"}), 503
    
    try:
        # 检查设备是否存在
        existing_device = data_manager.get_device(device_id)
        if not existing_device:
            return jsonify({"error": f"未找到设备ID为{device_id}的设备"}), 404
        
        # 删除设备
        success = data_manager.delete_device(device_id)
        
        if success:
            return jsonify({
                "success": True,
                "message": f"成功删除设备: {device_id}"
            })
        else:
            return jsonify({
                "success": False,
                "error": "删除设备失败"
            }), 500
    except Exception as e:
        logger.error(f"删除设备{device_id}出错: {e}")
        return jsonify({"error": str(e)}), 500

@devices_bp.route('/<device_id>/tags', methods=['POST'])
def add_device_tag(device_id):
    """添加设备标签"""
    if not data_manager_available:
        return jsonify({"error": "数据管理器不可用"}), 503
    
    try:
        # 获取请求数据
        data = request.get_json()
        if not data or "tag" not in data:
            return jsonify({"error": "缺少标签数据"}), 400
        
        tag = data["tag"]
        
        # 检查设备是否存在
        device = data_manager.get_device(device_id)
        if not device:
            return jsonify({"error": f"未找到设备ID为{device_id}的设备"}), 404
        
        # 添加标签
        if "tags" not in device or not isinstance(device["tags"], list):
            device["tags"] = []
        
        if tag not in device["tags"]:
            device["tags"].append(tag)
            
            # 更新设备
            success = data_manager.update_device(device_id, device)
            
            if success:
                return jsonify({
                    "success": True,
                    "message": f"成功添加标签: {tag}",
                    "tags": device["tags"]
                })
            else:
                return jsonify({
                    "success": False,
                    "error": "添加标签失败"
                }), 500
        else:
            return jsonify({
                "success": True,
                "message": f"标签已存在: {tag}",
                "tags": device["tags"]
            })
    except Exception as e:
        logger.error(f"为设备{device_id}添加标签出错: {e}")
        return jsonify({"error": str(e)}), 500

@devices_bp.route('/<device_id>/tags/<tag>', methods=['DELETE'])
def remove_device_tag(device_id, tag):
    """删除设备标签"""
    if not data_manager_available:
        return jsonify({"error": "数据管理器不可用"}), 503
    
    try:
        # 检查设备是否存在
        device = data_manager.get_device(device_id)
        if not device:
            return jsonify({"error": f"未找到设备ID为{device_id}的设备"}), 404
        
        # 删除标签
        if "tags" in device and isinstance(device["tags"], list) and tag in device["tags"]:
            device["tags"].remove(tag)
            
            # 更新设备
            success = data_manager.update_device(device_id, device)
            
            if success:
                return jsonify({
                    "success": True,
                    "message": f"成功删除标签: {tag}",
                    "tags": device["tags"]
                })
            else:
                return jsonify({
                    "success": False,
                    "error": "删除标签失败"
                }), 500
        else:
            return jsonify({
                "success": True,
                "message": f"标签不存在: {tag}",
                "tags": device.get("tags", [])
            })
    except Exception as e:
        logger.error(f"为设备{device_id}删除标签出错: {e}")
        return jsonify({"error": str(e)}), 500 
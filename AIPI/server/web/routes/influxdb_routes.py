from flask import Blueprint, jsonify, request
import os
import logging
import sys
from typing import Dict, List, Any, Optional, Union
import json
import time
from datetime import datetime, timedelta

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
influxdb_bp = Blueprint('influxdb', __name__, url_prefix='/api/influxdb')

# 日志配置
logger = logging.getLogger(__name__)

@influxdb_bp.route('/status', methods=['GET'])
def check_status():
    """检查InfluxDB连接状态"""
    if not data_manager_available:
        return jsonify({"status": "error", "message": "数据管理器不可用"}), 503
    
    try:
        # 尝试连接数据库
        is_connected = data_manager._connect()
        
        return jsonify({
            "status": "connected" if is_connected else "disconnected",
            "url": data_manager.influx_url,
            "org": data_manager.influx_org,
            "bucket": data_manager.influx_bucket
        })
    except Exception as e:
        logger.error(f"检查InfluxDB状态出错: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@influxdb_bp.route('/data/<device_id>', methods=['GET'])
def query_device_data(device_id):
    """查询设备数据"""
    if not data_manager_available:
        return jsonify({"error": "数据管理器不可用"}), 503
    
    # 获取查询参数
    measurement = request.args.get('measurement', 'device_data')
    start_time = request.args.get('start', '-1h')
    limit = int(request.args.get('limit', '100'))
    
    try:
        data = data_manager.query_device_data(
            device_id=device_id,
            measurement=measurement,
            start_time=start_time,
            limit=limit
        )
        
        return jsonify({
            "device_id": device_id,
            "measurement": measurement,
            "start_time": start_time,
            "limit": limit,
            "data": data
        })
    except Exception as e:
        logger.error(f"查询设备数据出错: {e}")
        return jsonify({"error": str(e)}), 500

@influxdb_bp.route('/data/<device_id>', methods=['POST'])
def write_device_data(device_id):
    """写入设备数据"""
    if not data_manager_available:
        return jsonify({"error": "数据管理器不可用"}), 503
    
    try:
        # 获取请求数据
        data = request.get_json()
        if not data:
            return jsonify({"error": "缺少数据"}), 400
        
        # 写入数据
        success = data_manager.write_device_data(device_id, data)
        
        if success:
            return jsonify({
                "success": True,
                "message": "数据写入成功",
                "device_id": device_id,
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "success": False,
                "message": "数据写入失败"
            }), 500
            
    except Exception as e:
        logger.error(f"写入设备数据出错: {e}")
        return jsonify({"error": str(e)}), 500

@influxdb_bp.route('/alerts/<device_id>', methods=['POST'])
def create_alert(device_id):
    """创建设备警报"""
    if not data_manager_available:
        return jsonify({"error": "数据管理器不可用"}), 503
    
    try:
        # 获取请求数据
        data = request.get_json()
        if not data:
            return jsonify({"error": "缺少数据"}), 400
        
        # 必需的字段
        alert_type = data.get('alert_type')
        message = data.get('message')
        
        if not alert_type or not message:
            return jsonify({"error": "缺少必需的字段: alert_type, message"}), 400
        
        # 可选字段
        severity = data.get('severity', 'info')
        extra_data = data.get('data', {})
        
        # 写入警报
        success = data_manager.write_alert(
            device_id=device_id,
            alert_type=alert_type,
            message=message,
            severity=severity,
            data=extra_data
        )
        
        if success:
            return jsonify({
                "success": True,
                "message": "警报创建成功",
                "device_id": device_id,
                "alert_type": alert_type,
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "success": False,
                "message": "警报创建失败"
            }), 500
            
    except Exception as e:
        logger.error(f"创建警报出错: {e}")
        return jsonify({"error": str(e)}), 500

@influxdb_bp.route('/alerts/<device_id>', methods=['GET'])
def get_device_alerts(device_id):
    """获取设备警报"""
    if not data_manager_available:
        return jsonify({"error": "数据管理器不可用"}), 503
    
    # 获取查询参数
    start_time = request.args.get('start', '-24h')
    limit = int(request.args.get('limit', '100'))
    
    try:
        data = data_manager.query_device_data(
            device_id=device_id,
            measurement='alerts',
            start_time=start_time,
            limit=limit
        )
        
        return jsonify({
            "device_id": device_id,
            "start_time": start_time,
            "limit": limit,
            "alerts": data
        })
    except Exception as e:
        logger.error(f"获取设备警报出错: {e}")
        return jsonify({"error": str(e)}), 500

@influxdb_bp.route('/commands/<device_id>', methods=['GET'])
def get_device_commands(device_id):
    """获取设备命令历史"""
    if not data_manager_available:
        return jsonify({"error": "数据管理器不可用"}), 503
    
    # 获取查询参数
    start_time = request.args.get('start', '-24h')
    limit = int(request.args.get('limit', '100'))
    
    try:
        data = data_manager.query_device_data(
            device_id=device_id,
            measurement='command_results',
            start_time=start_time,
            limit=limit
        )
        
        return jsonify({
            "device_id": device_id,
            "start_time": start_time,
            "limit": limit,
            "commands": data
        })
    except Exception as e:
        logger.error(f"获取设备命令历史出错: {e}")
        return jsonify({"error": str(e)}), 500 
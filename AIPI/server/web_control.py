import os
import time
import json
import logging
import threading
import jwt
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from werkzeug.security import check_password_hash
from config import WEB_CONFIG, LOG_CONFIG, JWT_CONFIG
from mqtt_client import get_mqtt_client
from device_controller import execute_device_action, get_device_status
from influx_writer import query_latest_data

# 配置日志
logging.basicConfig(
    level=LOG_CONFIG["level"],
    format=LOG_CONFIG["format"],
    filename=LOG_CONFIG.get("filename")
)
logger = logging.getLogger("web_control")

# 创建Flask应用
app = Flask(__name__, static_folder='../nextjs_frontend/out', static_url_path='')
CORS(app)

# 配置SocketIO
socketio = SocketIO(app, cors_allowed_origins=WEB_CONFIG["cors_origins"])

# MQTT客户端
mqtt_client = get_mqtt_client()

# 当前连接的客户端计数
connected_clients = 0

# 设备数据缓存
device_data_cache = {}

# 最后一次更新时间
last_update_time = {}

# JWT黑名单
token_blacklist = set()

# 用户会话
user_sessions = {}

# 验证JWT令牌
def verify_token(token):
    """
    验证JWT令牌
    :param token: JWT令牌
    :return: 令牌有效返回解码后的数据，否则返回None
    """
    try:
        if token in token_blacklist:
            return None
            
        decoded = jwt.decode(
            token, 
            JWT_CONFIG["secret_key"],
            algorithms=[JWT_CONFIG["algorithm"]]
        )
        
        # 检查是否过期
        if decoded.get("exp") < time.time():
            return None
            
        return decoded
        
    except jwt.PyJWTError:
        return None

# 需要认证的路由装饰器
def requires_auth(f):
    def decorated(*args, **kwargs):
        # 从请求头获取令牌
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"error": "未提供有效的认证令牌"}), 401
            
        token = auth_header.split(' ')[1]
        
        # 验证令牌
        decoded = verify_token(token)
        if not decoded:
            return jsonify({"error": "认证令牌无效或已过期"}), 401
            
        # 将解码后的令牌信息添加到请求上下文
        request.user = decoded
        
        return f(*args, **kwargs)
    
    # 添加此行以保持路由名称
    decorated.__name__ = f.__name__
    return decorated

# WebSocket认证中间件
@socketio.on('authenticate')
def handle_authentication(auth_data):
    """
    WebSocket认证
    :param auth_data: 包含token字段的认证数据
    """
    token = auth_data.get('token')
    if not token:
        emit('auth_response', {'success': False, 'message': '未提供认证令牌'})
        return
    
    decoded = verify_token(token)
    if not decoded:
        emit('auth_response', {'success': False, 'message': '认证令牌无效或已过期'})
        return
    
    # 保存会话信息
    session_id = request.sid
    user_id = decoded.get('user_id')
    user_sessions[session_id] = {
        'user_id': user_id,
        'username': decoded.get('username'),
        'role': decoded.get('role'),
        'connected_at': time.time()
    }
    
    emit('auth_response', {
        'success': True, 
        'message': '认证成功',
        'user': {
            'id': user_id,
            'username': decoded.get('username'),
            'role': decoded.get('role')
        }
    })
    
    # 发送当前设备状态
    emit('device_status_batch', get_all_device_status())

# WebSocket连接/断开事件
@socketio.on('connect')
def handle_connect():
    """处理新的WebSocket连接"""
    global connected_clients
    connected_clients += 1
    logger.info(f"新的WebSocket连接，当前连接数: {connected_clients}")

@socketio.on('disconnect')
def handle_disconnect():
    """处理WebSocket断开连接"""
    global connected_clients
    connected_clients -= 1
    
    # 清理会话
    session_id = request.sid
    if session_id in user_sessions:
        del user_sessions[session_id]
    
    logger.info(f"WebSocket连接断开，当前连接数: {connected_clients}")

# API路由：登录
@app.route('/api/login', methods=['POST'])
def login():
    """
    用户登录
    :return: JWT令牌
    """
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"error": "请提供用户名和密码"}), 400
    
    # 检查用户认证信息
    users = WEB_CONFIG.get("users", {})
    if username not in users:
        # 为了安全，不提示具体是用户名还是密码错误
        return jsonify({"error": "用户名或密码不正确"}), 401
    
    user_info = users[username]
    if not check_password_hash(user_info["password_hash"], password):
        return jsonify({"error": "用户名或密码不正确"}), 401
    
    # 生成JWT令牌
    expiration = datetime.utcnow() + timedelta(hours=JWT_CONFIG.get("expiration_hours", 24))
    token_data = {
        "user_id": user_info.get("id", username),
        "username": username,
        "role": user_info.get("role", "user"),
        "exp": expiration.timestamp()
    }
    
    token = jwt.encode(
        token_data,
        JWT_CONFIG["secret_key"],
        algorithm=JWT_CONFIG["algorithm"]
    )
    
    return jsonify({
        "token": token,
        "expires": expiration.timestamp(),
        "user": {
            "id": user_info.get("id", username),
            "username": username,
            "role": user_info.get("role", "user"),
            "display_name": user_info.get("display_name", username)
        }
    })

# API路由：登出
@app.route('/api/logout', methods=['POST'])
@requires_auth
def logout():
    """
    用户登出
    :return: 成功状态
    """
    # 获取令牌并加入黑名单
    auth_header = request.headers.get('Authorization')
    token = auth_header.split(' ')[1]
    token_blacklist.add(token)
    
    return jsonify({"success": True, "message": "登出成功"})

# API路由：获取设备状态
@app.route('/api/devices', methods=['GET'])
@requires_auth
def get_devices():
    """
    获取所有设备状态
    :return: 设备状态列表
    """
    return jsonify(get_all_device_status())

# API路由：获取单个设备状态
@app.route('/api/devices/<device_id>', methods=['GET'])
@requires_auth
def get_device_detail(device_id):
    """
    获取单个设备详细状态
    :param device_id: 设备ID
    :return: 设备详细状态
    """
    # 获取设备基本状态
    status = get_device_status(device_id)
    
    # 获取设备最新历史数据
    try:
        latest_data = query_latest_data(device_id)
        
        # 合并数据
        if latest_data:
            status = {**status, **latest_data}
    except Exception as e:
        logger.error(f"获取设备 {device_id} 历史数据时出错: {str(e)}")
    
    return jsonify(status)

# API路由：设备控制
@app.route('/api/devices/<device_id>/control', methods=['POST'])
@requires_auth
def control_device(device_id):
    """
    控制设备
    :param device_id: 设备ID
    :return: 控制结果
    """
    data = request.json
    action = data.get('action')
    parameters = data.get('parameters', {})
    
    if not action:
        return jsonify({"error": "未提供控制动作"}), 400
    
    # 记录操作者信息
    username = request.user.get('username', 'unknown')
    logger.info(f"用户 {username} 控制设备 {device_id}: {action} {parameters}")
    
    # 执行设备控制
    result = execute_device_action(device_id, action, parameters)
    
    # 如果成功，通过MQTT发布控制结果
    if result.get("success", False):
        control_data = {
            "device_id": device_id,
            "action": action,
            "parameters": parameters,
            "user": username,
            "timestamp": time.time(),
            "result": result
        }
        mqtt_client.publish("device/control/web", json.dumps(control_data))
        
        # 通过WebSocket推送状态更新
        socketio.emit('device_status_update', {
            "device_id": device_id,
            "status": get_device_status(device_id).get(device_id, "unknown"),
            "timestamp": time.time()
        })
    
    return jsonify(result)

# API路由：获取设备历史数据
@app.route('/api/devices/<device_id>/history', methods=['GET'])
@requires_auth
def get_device_history(device_id):
    """
    获取设备历史数据
    :param device_id: 设备ID
    :return: 历史数据
    """
    time_range = request.args.get('range', '1h')
    fields = request.args.get('fields')
    
    if fields:
        fields = fields.split(',')
    
    try:
        # 查询历史数据
        data = query_latest_data(device_id, fields, time_range)
        return jsonify(data or {})
    except Exception as e:
        logger.error(f"获取设备 {device_id} 历史数据时出错: {str(e)}")
        return jsonify({"error": str(e)}), 500

# API路由：设备数据监控
@app.route('/api/monitor', methods=['GET'])
@requires_auth
def get_monitor_data():
    """
    获取实时监控数据
    :return: 监控数据
    """
    # 返回所有设备的最新数据
    return jsonify({
        "devices": get_all_device_status(),
        "timestamp": time.time()
    })

# 获取所有设备状态
def get_all_device_status():
    """
    获取所有设备状态，包括最新数据
    :return: 设备状态字典
    """
    status = get_device_status()
    
    # 添加最新数据
    for device_id in status:
        try:
            latest_data = device_data_cache.get(device_id, {})
            if latest_data:
                status[device_id] = {
                    "status": status[device_id],
                    **latest_data,
                    "last_update": last_update_time.get(device_id, 0)
                }
        except Exception as e:
            logger.error(f"获取设备 {device_id} 缓存数据时出错: {str(e)}")
    
    return status

# MQTT消息处理
def mqtt_message_handler():
    """处理MQTT消息并更新WebSocket客户端"""
    # 确保MQTT客户端连接
    if not mqtt_client.connected:
        mqtt_client.connect()
    
    # 订阅设备数据主题
    device_data_topic = "device/+/data"
    mqtt_client.client.message_callback_add(device_data_topic, on_device_data)
    mqtt_client.client.subscribe(device_data_topic)
    
    # 订阅设备控制结果主题
    control_result_topic = "device/control/result"
    mqtt_client.client.message_callback_add(control_result_topic, on_control_result)
    mqtt_client.client.subscribe(control_result_topic)
    
    logger.info("MQTT消息处理器已启动")

# 设备数据消息回调
def on_device_data(client, userdata, msg):
    """
    处理设备数据消息
    :param client: MQTT客户端
    :param userdata: 用户数据
    :param msg: 消息
    """
    try:
        topic = msg.topic
        payload = json.loads(msg.payload.decode('utf-8'))
        
        # 从主题中提取设备ID，格式：device/{device_id}/data
        device_id = topic.split('/')[1]
        
        # 更新设备数据缓存
        device_data_cache[device_id] = payload
        last_update_time[device_id] = time.time()
        
        # 通过WebSocket推送实时数据
        socketio.emit('device_data_update', {
            "device_id": device_id,
            "data": payload,
            "timestamp": time.time()
        })
        
    except json.JSONDecodeError:
        logger.warning(f"无法解析MQTT消息为JSON: {msg.payload}")
    except Exception as e:
        logger.error(f"处理MQTT设备数据消息时出错: {str(e)}")

# 控制结果消息回调
def on_control_result(client, userdata, msg):
    """
    处理设备控制结果消息
    :param client: MQTT客户端
    :param userdata: 用户数据
    :param msg: 消息
    """
    try:
        payload = json.loads(msg.payload.decode('utf-8'))
        device_id = payload.get("device_id")
        
        # 通过WebSocket推送控制结果
        socketio.emit('control_result', payload)
        
        # 更新设备状态
        socketio.emit('device_status_update', {
            "device_id": device_id,
            "status": get_device_status(device_id).get(device_id, "unknown"),
            "timestamp": time.time()
        })
        
    except json.JSONDecodeError:
        logger.warning(f"无法解析MQTT控制结果消息为JSON: {msg.payload}")
    except Exception as e:
        logger.error(f"处理MQTT控制结果消息时出错: {str(e)}")

# 前端路由（处理SPA的路由）
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    """
    提供前端静态文件或回退到index.html
    :param path: 请求路径
    :return: 静态文件或index.html
    """
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

def start_web_server():
    """启动Web服务器"""
    # 启动MQTT消息处理
    mqtt_thread = threading.Thread(target=mqtt_message_handler)
    mqtt_thread.daemon = True
    mqtt_thread.start()
    
    # 启动SocketIO服务器
    host = WEB_CONFIG.get("host", "0.0.0.0")
    port = WEB_CONFIG.get("port", 5000)
    debug = WEB_CONFIG.get("debug", False)
    
    logger.info(f"启动Web服务器: {host}:{port}")
    socketio.run(app, host=host, port=port, debug=debug)

if __name__ == "__main__":
    start_web_server() 
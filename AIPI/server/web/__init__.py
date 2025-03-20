"""
树莓派AI命令控制中心Web模块

此包提供基于Flask的Web界面，用于远程控制和监控树莓派设备。
通过自然语言命令，结合LangChain和MQTT实现智能化设备控制。
"""

__version__ = "1.0.0"

import os
import sys
import logging
from flask import Flask

# 添加父目录到路径，以便导入父目录中的模块
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# 导入服务器配置
try:
    from config import LOG_CONFIG, WEB_CONFIG
    use_server_config = True
except ImportError:
    use_server_config = False

# 配置日志
if use_server_config and LOG_CONFIG:
    log_level = LOG_CONFIG.get("level", logging.INFO)
    log_format = LOG_CONFIG.get("format", '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    log_file = LOG_CONFIG.get("filename")
    
    logging_config = {
        "level": log_level,
        "format": log_format
    }
    
    # 在Windows下不指定encoding参数，避免冲突
    if sys.platform != 'win32':
        logging_config["encoding"] = 'utf-8'
        
    if log_file:
        logging_config["filename"] = log_file
        
    logging.basicConfig(**logging_config)
else:
    # 使用默认配置
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        # 在Windows下不指定encoding参数，避免冲突
        **({"encoding": 'utf-8'} if sys.platform != 'win32' else {})
    )

logger = logging.getLogger(__name__)

def create_app(config=None):
    """创建Flask应用实例"""
    # 创建应用
    app = Flask(__name__)
    
    # 加载默认配置
    if use_server_config and WEB_CONFIG:
        app.config.from_mapping(
            SECRET_KEY=WEB_CONFIG.get("secret_key", "dev"),
            GRAFANA_URL=os.environ.get('GRAFANA_URL', 'http://localhost:3000'),
            DEBUG=WEB_CONFIG.get("debug", False),
            HOST=WEB_CONFIG.get("host", "0.0.0.0"),
            PORT=WEB_CONFIG.get("port", 5000),
            WEBSOCKET_PORT=WEB_CONFIG.get("websocket_port", 5001)
        )
        logger.info("已从服务器配置加载Web配置")
    else:
        app.config.from_mapping(
            SECRET_KEY=os.environ.get('SECRET_KEY', 'dev'),
            GRAFANA_URL=os.environ.get('GRAFANA_URL', 'http://localhost:3000'),
            DEBUG=os.environ.get('WEB_DEBUG', 'False').lower() == 'true',
            HOST=os.environ.get('WEB_HOST', '0.0.0.0'),
            PORT=int(os.environ.get('WEB_PORT', '5000')),
            WEBSOCKET_PORT=int(os.environ.get('WEBSOCKET_PORT', '5001'))
        )
        logger.info("使用环境变量加载Web配置")
    
    # 应用额外配置
    if config:
        app.config.update(config)
    
    # 注册蓝图
    register_blueprints(app)
    
    # 注册错误处理器
    register_error_handlers(app)
    
    return app

def register_blueprints(app):
    """注册所有蓝图"""
    try:
        # 导入Grafana路由蓝图
        from .routes.grafana_routes import grafana_bp
        app.register_blueprint(grafana_bp)
        logger.info("已注册Grafana路由蓝图")
    except ImportError as e:
        logger.warning(f"无法导入Grafana路由蓝图: {e}")
    
    try:
        # 导入InfluxDB路由蓝图
        from .routes.influxdb_routes import influxdb_bp
        app.register_blueprint(influxdb_bp)
        logger.info("已注册InfluxDB路由蓝图")
    except ImportError as e:
        logger.warning(f"无法导入InfluxDB路由蓝图: {e}")
    
    try:
        # 导入设备管理路由蓝图
        from .routes.devices_routes import devices_bp
        app.register_blueprint(devices_bp)
        logger.info("已注册设备管理路由蓝图")
    except ImportError as e:
        logger.warning(f"无法导入设备管理路由蓝图: {e}")
    
    # 这里可以继续注册其他蓝图

def register_error_handlers(app):
    """注册错误处理器"""
    @app.errorhandler(404)
    def page_not_found(e):
        return {
            "error": "Not Found",
            "message": "请求的资源不存在"
        }, 404
    
    @app.errorhandler(500)
    def internal_server_error(e):
        return {
            "error": "Internal Server Error",
            "message": "服务器内部错误"
        }, 500 
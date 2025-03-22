"""
API模块 - 提供RESTful API功能
"""
import logging
from flask import Blueprint, Flask

# 日志配置
logger = logging.getLogger(__name__)

def setup_routes(app: Flask):
    """设置API路由"""
    # 导入蓝图
    from routes.devices_routes import devices_bp
    
    try:
        # 从Grafana路由导入
        from routes.grafana_routes import grafana_bp
        app.register_blueprint(grafana_bp)
        logger.info("已注册Grafana API蓝图")
    except ImportError as e:
        logger.warning(f"无法导入Grafana API蓝图: {e}")
    
    try:
        # 从InfluxDB路由导入
        from routes.influxdb_routes import influxdb_bp
        app.register_blueprint(influxdb_bp)
        logger.info("已注册InfluxDB API蓝图")
    except ImportError as e:
        logger.warning(f"无法导入InfluxDB API蓝图: {e}")
    
    # 注册设备蓝图
    app.register_blueprint(devices_bp)
    logger.info("已注册设备API蓝图")
    
    # 添加无需蓝图的API路由
    @app.route('/api/status')
    def api_status():
        """API状态检查"""
        from flask import jsonify
        return jsonify({
            "status": "running",
            "version": "1.0.0",
            "timestamp": __import__('datetime').datetime.now().isoformat()
        }) 
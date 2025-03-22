from flask import Blueprint, jsonify, request, redirect, current_app
import os
import logging
import sys
from typing import Dict, List, Any, Optional
import requests

# 添加项目根目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# 导入Grafana仪表盘管理器
try:
    sys.path.append('/work/AISA/AIPI/server')
    from grafana.grafana_dashboard_config import get_dashboard_manager
    dashboard_manager = get_dashboard_manager()
    dashboard_manager_available = True
except ImportError as e:
    print(f"无法导入Grafana仪表盘管理器: {e}")
    dashboard_manager_available = False

# 创建Blueprint
grafana_bp = Blueprint('grafana', __name__, url_prefix='/grafana')

# 日志配置
logger = logging.getLogger(__name__)

@grafana_bp.route('/dashboards', methods=['GET'])
def list_dashboards():
    """获取所有可用的仪表盘"""
    if not dashboard_manager_available:
        return jsonify({"error": "Grafana仪表盘管理器不可用"}), 503
    
    try:
        # 检查是否需要刷新
        refresh = request.args.get('refresh', 'false').lower() == 'true'
        if refresh:
            dashboard_manager.reload_dashboards()
            
            # 尝试导入到Grafana
            try:
                import_result = dashboard_manager.import_dashboards_to_grafana()
                if import_result:
                    logger.info("成功导入仪表盘到Grafana")
                else:
                    logger.warning("导入仪表盘到Grafana失败")
            except Exception as e:
                logger.error(f"导入仪表盘到Grafana出错: {e}")
        
        dashboards = dashboard_manager.get_dashboard_list()
        return jsonify({"dashboards": dashboards})
    except Exception as e:
        logger.error(f"获取仪表盘列表出错: {e}")
        return jsonify({"error": str(e)}), 500

@grafana_bp.route('/dashboards/tag/<tag>', methods=['GET'])
def get_dashboards_by_tag(tag):
    """按标签获取Grafana仪表盘"""
    if not dashboard_manager_available:
        return jsonify({"error": "Grafana仪表盘管理器不可用"}), 503
    
    try:
        dashboards = dashboard_manager.get_dashboard_by_tag(tag)
        return jsonify({
            "tag": tag,
            "dashboards": dashboards,
            "count": len(dashboards)
        })
    except Exception as e:
        logger.error(f"按标签获取仪表盘出错: {e}")
        return jsonify({"error": str(e)}), 500

@grafana_bp.route('/dashboards/<uid>', methods=['GET'])
def get_dashboard_config(uid):
    """获取指定仪表盘的配置"""
    if not dashboard_manager_available:
        return jsonify({"error": "Grafana仪表盘管理器不可用"}), 503
    
    try:
        config = dashboard_manager.get_dashboard_config(uid)
        if config:
            return jsonify(config)
        else:
            return jsonify({"error": f"找不到UID为{uid}的仪表盘"}), 404
    except Exception as e:
        logger.error(f"获取仪表盘配置出错: {e}")
        return jsonify({"error": str(e)}), 500

@grafana_bp.route('/embed/<uid>', methods=['GET'])
def get_embedded_dashboard_url(uid):
    """获取嵌入式仪表盘URL"""
    if not dashboard_manager_available:
        logger.warning("Grafana仪表盘管理器不可用，无法获取嵌入URL")
        return jsonify({
            "success": False,
            "error": "Grafana仪表盘管理器不可用，请检查配置",
            "embed_url": None
        }), 503
    
    try:
        # 获取设备ID参数（可选）
        device_id = request.args.get('device_id')
        
        # 获取嵌入URL
        embed_url = dashboard_manager.get_embed_url(uid, device_id)
        
        if not embed_url:
            logger.warning(f"未找到UID为 {uid} 的仪表盘")
            return jsonify({
                "success": False,
                "error": f"未找到UID为 {uid} 的仪表盘", 
                "embed_url": None
            }), 404
            
        logger.info(f"成功获取仪表盘 {uid} 的嵌入URL")
        return jsonify({
            "success": True,
            "embed_url": embed_url,
            "dashboard_uid": uid
        })
    except Exception as e:
        logger.error(f"获取嵌入URL错误: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "embed_url": None
        }), 500

@grafana_bp.route('/redirect/<uid>', methods=['GET'])
def redirect_to_dashboard(uid):
    """重定向到Grafana仪表盘"""
    if not dashboard_manager_available:
        return jsonify({"error": "Grafana仪表盘管理器不可用"}), 503
    
    # 获取查询参数
    device_id = request.args.get('device_id', '*')
    
    try:
        # 构建Grafana URL
        grafana_url = os.getenv("GRAFANA_URL", "http://localhost:3000")
        
        # 获取模板变量
        variables = dashboard_manager.get_template_variables(uid)
        var_params = []
        
        # 添加设备ID变量
        if 'device' in variables:
            var_params.append(f"var-device={device_id}")
        
        # 添加bucket变量
        if 'bucket' in variables:
            bucket = os.getenv("INFLUX_BUCKET", "iot_data") 
            var_params.append(f"var-bucket={bucket}")
        
        # 构建完整URL
        dashboard_url = f"{grafana_url}/d/{uid}?{('&'.join(var_params))}"
        
        return redirect(dashboard_url)
    except Exception as e:
        logger.error(f"重定向到仪表盘出错: {e}")
        return jsonify({"error": str(e)}), 500

@grafana_bp.route('/reload', methods=['POST'])
def reload_dashboards():
    """重新加载所有仪表盘配置"""
    if not dashboard_manager_available:
        return jsonify({"error": "Grafana仪表盘管理器不可用"}), 503
    
    try:
        dashboard_manager.reload_dashboards()
        return jsonify({
            "success": True,
            "message": "成功重新加载仪表盘配置",
            "dashboard_count": dashboard_manager.dashboard_count
        })
    except Exception as e:
        logger.error(f"重新加载仪表盘配置出错: {e}")
        return jsonify({"error": str(e)}), 500

@grafana_bp.route('/import', methods=['POST'])
def import_dashboards():
    """手动导入仪表盘到Grafana"""
    if not dashboard_manager_available:
        return jsonify({"error": "Grafana仪表盘管理器不可用"}), 503
    
    try:
        # 首先刷新仪表盘配置
        dashboard_manager.reload_dashboards()
        
        # 导入到Grafana
        import_result = dashboard_manager.import_dashboards_to_grafana()
        
        if import_result:
            return jsonify({
                "success": True, 
                "message": "成功导入仪表盘到Grafana", 
                "count": dashboard_manager.dashboard_count
            })
        else:
            return jsonify({
                "success": False, 
                "message": "导入仪表盘到Grafana失败，请检查日志"
            }), 500
    except Exception as e:
        logger.error(f"导入仪表盘出错: {e}")
        return jsonify({"error": str(e)}), 500

@grafana_bp.route('/proxy/<path:url>', methods=['GET'])
def proxy_grafana(url):
    """代理Grafana请求，解决跨域问题"""
    try:
        grafana_url = os.getenv("GRAFANA_URL", "http://localhost:3000")
        if not grafana_url.endswith('/'):
            grafana_url += '/'
        
        # 构建完整URL
        full_url = f"{grafana_url}{url}"
        logger.info(f"代理Grafana请求: {full_url}")
        
        # 转发原始请求的所有参数
        params = request.args.to_dict()
        
        # 发送请求到Grafana
        response = requests.get(full_url, params=params, stream=True)
        
        # 返回响应给客户端
        return (response.content, response.status_code, response.headers.items())
    except Exception as e:
        logger.error(f"代理Grafana请求出错: {e}")
        return jsonify({"error": f"代理请求失败: {str(e)}"}), 500

@grafana_bp.route('/view/<uid>', methods=['GET'])
def view_dashboard(uid):
    """显示仪表盘内容"""
    if not dashboard_manager_available:
        return "Grafana仪表盘管理器不可用", 503
    
    try:
        # 获取设备ID参数（可选）
        device_id = request.args.get('device_id', '')
        
        # 获取对应仪表盘的信息
        dashboards = dashboard_manager.get_dashboard_list()
        dashboard_title = "仪表盘"
        
        for dashboard in dashboards:
            if dashboard.get('uid') == uid:
                dashboard_title = dashboard.get('title', "仪表盘")
                break
        
        # 构造HTML页面
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{dashboard_title}</title>
            <style>
                body {{ margin: 0; padding: 0; overflow: hidden; }}
                iframe {{ border: none; width: 100%; height: 100vh; }}
            </style>
        </head>
        <body>
            <iframe src="/grafana/proxy/d/{uid}?orgId=1&kiosk&var-device_id={device_id}" allowfullscreen></iframe>
        </body>
        </html>
        """
        
        return html
    except Exception as e:
        logger.error(f"显示仪表盘出错: {e}")
        return f"显示仪表盘出错: {str(e)}", 500 
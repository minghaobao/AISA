#!/usr/bin/env python3
"""
集成版服务器 - 同时提供API和前端功能
"""
import os
import sys
import logging
import argparse
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    # 在Python 3.9+中才使用encoding参数
    **({"encoding": 'utf-8'} if sys.version_info >= (3, 9) else {})
)
logger = logging.getLogger("integrated_server")

# 添加项目根目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# 加载环境变量
try:
    # 尝试查找.env文件
    env_path = find_dotenv(raise_error_if_not_found=False)
    if env_path:
        logger.info(f"找到.env文件: {env_path}")
        load_dotenv(env_path)
        
    # 检查API密钥是否加载
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        # 安全输出密钥前几位和后几位，中间部分隐藏
        masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "***"
        logger.info(f"已加载API密钥: {masked_key}")
    else:
        logger.warning("未找到API密钥，请检查.env文件或环境变量")
except Exception as e:
    logger.error(f"加载环境变量出错: {e}")

def check_dependencies():
    """检查必要的依赖是否已安装"""
    missing = []
    for module in ["flask", "dotenv", "paho.mqtt", "langchain", "langchain_openai"]:
        try:
            __import__(module.replace("-", "_"))
        except ImportError:
            missing.append(module)
    
    if missing:
        logger.error(f"缺少必要的依赖: {', '.join(missing)}")
        logger.info("请运行: pip install -r requirements.txt")
        return False
    return True

def create_app(args):
    """创建Flask应用"""
    # 导入Flask应用(先确保所有依赖都安装好了)
    try:
        from flask import Flask
        
        # 创建应用
        app = Flask(__name__)
        
        # 从web模块导入前端界面
        from web.app import setup_routes as setup_web_routes
        from web.app import setup_mqtt
        
        # 从api模块导入API路由
        from api import setup_routes as setup_api_routes
        
        # 设置路由
        setup_web_routes(app)
        setup_api_routes(app)
        
        # 初始化MQTT连接
        app.before_request(setup_mqtt())
        
        # 添加调试路由
        @app.route('/debug/routes')
        def list_routes():
            """列出所有注册的路由"""
            from flask import jsonify
            routes = []
            for rule in app.url_map.iter_rules():
                routes.append({
                    "endpoint": rule.endpoint,
                    "methods": list(rule.methods),
                    "path": str(rule)
                })
            return jsonify({"routes": routes})
        
        logger.info("成功创建集成应用")
        return app
    except ImportError as e:
        logger.error(f"导入Flask模块出错: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"创建应用出错: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        sys.exit(1)

def main():
    """主程序入口"""
    parser = argparse.ArgumentParser(description="启动集成服务器")
    parser.add_argument("--host", default="0.0.0.0", help="绑定主机地址")
    parser.add_argument("--port", type=int, default=5000, help="绑定端口")
    parser.add_argument("--debug", action="store_true", help="启用调试模式")
    parser.add_argument("--model", default="gpt-3.5-turbo", help="使用的OpenAI模型")
    parser.add_argument("--no-api-check", action="store_true", help="跳过API连接检查")
    parser.add_argument("--api-key", help="直接指定OpenAI API密钥")
    
    args = parser.parse_args()
    
    # 处理命令行直接指定的API密钥
    if args.api_key:
        os.environ["OPENAI_API_KEY"] = args.api_key
        logger.info("已使用命令行参数设置API密钥")
    
    # 设置使用的模型
    os.environ["OPENAI_MODEL"] = args.model
    
    # 检查依赖
    if not check_dependencies():
        logger.error("缺少必要的依赖，无法启动")
        sys.exit(1)
    
    # 创建数据存储目录
    os.makedirs(os.path.join(current_dir, "data"), exist_ok=True)
    
    # 创建Flask应用
    app = create_app(args)
    if not app:
        logger.error("创建应用失败")
        sys.exit(1)
    
    # 启动应用
    try:
        logger.info(f"启动集成服务器: http://{args.host}:{args.port}")
        logger.info(f"使用模型: {args.model}")
        app.run(host=args.host, port=args.port, debug=args.debug)
    except Exception as e:
        logger.error(f"启动服务器出错: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("用户中断，程序退出")
    except Exception as e:
        logger.error(f"程序异常退出: {e}")
        import traceback
        logger.error(f"错误详情: {traceback.format_exc()}")
        sys.exit(1) 
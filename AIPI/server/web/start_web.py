#!/usr/bin/env python3
"""
树莓派AI命令控制中心 Web界面启动程序
"""
import os
import sys
import argparse
import logging
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

# 设置控制台编码为UTF-8
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    # 避免直接修改sys.stdout和sys.stderr，这会导致与logging冲突
    try:
        import locale
        locale.setlocale(locale.LC_ALL, 'Chinese')
    except Exception as e:
        pass  # 忽略设置区域错误，继续执行

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    # 在Windows下不指定encoding参数，避免冲突
    **({"encoding": 'utf-8'} if sys.platform != 'win32' else {})
)
logger = logging.getLogger("web_starter")

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

def check_api_key():
    """检查OpenAI API密钥"""
    # 尝试加载.env文件
    env_path = find_dotenv(raise_error_if_not_found=False)
    if env_path:
        logger.info(f"找到.env文件: {env_path}")
        load_dotenv(env_path)
    
    # 检查API密钥
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("警告: 未设置OPENAI_API_KEY环境变量")
        logger.info("请在.env文件中设置OPENAI_API_KEY，或通过环境变量设置")
        return False
    
    # 确保API密钥被设置为环境变量
    os.environ["OPENAI_API_KEY"] = api_key
    
    # 掩码显示API密钥（只显示前4位和后4位）
    masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "***"
    logger.info(f"已加载API密钥: {masked_key}")
    return True

def check_openai_connection():
    """测试OpenAI API连接"""
    try:
        from langchain_openai import ChatOpenAI
        
        logger.info("测试OpenAI API连接...")
        llm = ChatOpenAI(temperature=0)
        response = llm.invoke("测试API连接，请回复'连接成功'")
        logger.info(f"API测试响应: {response}")
        logger.info("✓ API连接测试成功")
        return True
    except Exception as e:
        logger.error(f"API连接测试失败: {e}")
        logger.error("请检查API密钥和网络连接")
        return False

def main():
    """主程序入口"""
    parser = argparse.ArgumentParser(description="启动树莓派AI命令控制中心Web界面")
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
    
    # 确保我们在正确的目录
    current_dir = Path(__file__).parent.absolute()
    os.chdir(current_dir)
    
    # 将此目录加入到Python路径
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))
    
    # 检查API密钥
    if not check_api_key():
        logger.warning("继续启动，但AI功能可能无法正常工作")
    
    # 检查API连接
    if not args.no_api_check and os.getenv("OPENAI_API_KEY"):
        if not check_openai_connection():
            logger.warning("继续启动，但AI功能可能无法正常工作")
    
    # 检查依赖
    if not check_dependencies():
        logger.error("缺少必要的依赖，无法启动")
        sys.exit(1)
        
    # 导入Flask应用
    try:
        from app import app
        logger.info(f"启动Web服务器: http://{args.host}:{args.port}")
        logger.info(f"使用模型: {args.model}")
        app.run(host=args.host, port=args.port, debug=args.debug)
    except ImportError as e:
        logger.error(f"导入app模块出错: {e}")
        sys.exit(1)
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
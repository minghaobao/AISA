from flask import Flask, render_template, request, jsonify
import os
import sys
from dotenv import load_dotenv, find_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor
from langchain_core.agents import AgentFinish
from langchain.agents.agent_types import AgentType
from langchain.agents.format_scratchpad import format_to_openai_function_messages
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import BaseTool, tool
import json
import paho.mqtt.client as mqtt
import uuid
import time
import threading
import logging

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
    logger = logging.getLogger("flask_langchain")
    logger.info("成功导入数据管理器")
except ImportError as e:
    print(f"无法导入数据管理器: {e}")
    data_manager_available = False

# 导入Grafana仪表盘管理器
try:
    from ai_mqtt_langchain.grafana.grafana_dashboard_config import get_dashboard_manager
    dashboard_manager = get_dashboard_manager()
    dashboard_manager_available = True
except ImportError as e:
    print(f"无法导入Grafana仪表盘管理器: {e}")
    dashboard_manager_available = False

# 导入路由模块
routes_available = False
# 尝试导入本地routes目录下的grafana_routes
try:
    from routes.grafana_routes import grafana_bp
    from routes.devices_routes import devices_bp
    routes_available = True
    print("成功导入本地路由模块")
except ImportError as e:
    print(f"无法导入本地路由: {e}")
    # 如果本地导入失败，尝试从原始位置导入
    try:
        from ai_mqtt_langchain.web.routes.grafana_routes import grafana_bp
        from ai_mqtt_langchain.web.routes.influxdb_routes import influxdb_bp
        from ai_mqtt_langchain.web.routes.devices_routes import devices_bp
        routes_available = True
    except ImportError as e:
        print(f"无法导入路由模块: {e}")
        routes_available = False

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
    # 在Python 3.9+中才使用encoding参数
    **({"encoding": 'utf-8'} if sys.version_info >= (3, 9) else {})
)
logger = logging.getLogger("flask_langchain")

# 加载环境变量 - 确保从正确位置加载
try:
    # 尝试查找.env文件
    env_path = find_dotenv(raise_error_if_not_found=False)
    if env_path:
        logger.info(f"找到.env文件: {env_path}")
        load_dotenv(env_path)
        
    # 重新检查API密钥是否加载
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        # 安全输出密钥前几位和后几位，中间部分隐藏
        masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "***"
        logger.info(f"已加载API密钥: {masked_key}")
    else:
        logger.warning("未找到API密钥，请检查.env文件或环境变量")
except Exception as e:
    logger.error(f"加载环境变量出错: {e}")

app = Flask(__name__)

# 注册蓝图
if routes_available:
    app.register_blueprint(grafana_bp)
    logger.info("已注册Grafana蓝图")
    try:
        app.register_blueprint(devices_bp)
        logger.info("已注册设备管理蓝图")
    except NameError as e:
        logger.warning(f"设备管理蓝图未定义: {e}")
    try:
        app.register_blueprint(influxdb_bp)
        logger.info("已注册InfluxDB蓝图")
    except NameError as e:
        logger.warning(f"InfluxDB蓝图未定义: {e}")

# 全局变量
mqtt_host = os.getenv("MQTT_HOST", "localhost")
mqtt_port = int(os.getenv("MQTT_PORT", 1883))
mqtt_username = os.getenv("MQTT_USERNAME", "")
mqtt_password = os.getenv("MQTT_PASSWORD", "")
device_id = os.getenv("DEVICE_ID", "rpi_001")
results = {}
mqtt_connected = False

# MQTT客户端
client = mqtt.Client()

# 如果设置了用户名和密码，配置认证信息
if mqtt_username and mqtt_password:
    client.username_pw_set(mqtt_username, mqtt_password)
    logger.info(f"已配置MQTT认证信息，用户名: {mqtt_username}")
else:
    logger.warning("未配置MQTT认证信息，这可能导致连接被拒绝")

def on_connect(client, userdata, flags, rc):
    global mqtt_connected
    if rc == 0:
        mqtt_connected = True
        logger.info(f"已连接到MQTT服务器: {rc}")
        client.subscribe(f"device/{device_id}/result")
        client.subscribe(f"device/{device_id}/status")
    else:
        mqtt_connected = False
        logger.error(f"MQTT连接失败，返回码: {rc}")

def on_disconnect(client, userdata, rc):
    global mqtt_connected
    mqtt_connected = False
    logger.warning(f"MQTT断开连接，返回码: {rc}")
    # 尝试重新连接
    if rc != 0:
        logger.info("尝试重新连接MQTT服务器...")
        try_mqtt_connect()

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode('utf-8')
        data = json.loads(payload)
        
        if msg.topic.endswith("/result"):
            command_id = data.get("command_id")
            if command_id in results:
                results[command_id] = data
                logger.info(f"收到命令ID {command_id} 的结果")
        elif msg.topic.endswith("/status"):
            logger.info(f"设备状态更新: {data.get('status', 'unknown')}")
            
            # 将设备状态数据写入InfluxDB
            if data_manager_available and "system_info" in data:
                try:
                    # 提取系统信息数据
                    system_info = data.get("system_info", {})
                    if system_info and isinstance(system_info, dict):
                        # 写入设备数据
                        data_manager.write_device_data(
                            device_id=device_id,
                            data=system_info
                        )
                        logger.info(f"已记录设备状态数据到InfluxDB: {device_id}")
                except Exception as db_error:
                    logger.error(f"写入设备状态到InfluxDB失败: {db_error}")
    except Exception as e:
        logger.error(f"处理消息出错: {e}")

client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = on_message

# 连接MQTT
def try_mqtt_connect():
    global mqtt_connected
    try:
        client.connect(mqtt_host, mqtt_port, 60)
        client.loop_start()
        logger.info(f"MQTT客户端启动并尝试连接到 {mqtt_host}:{mqtt_port}")
    except Exception as e:
        mqtt_connected = False
        logger.error(f"MQTT连接错误: {e}")

# 初始化MQTT连接
def setup_mqtt():
    try_mqtt_connect()
    return before_request

# 初始化应用并启动MQTT
@app.before_request
def before_request():
    # 确保只执行一次，使用全局变量追踪状态
    if not hasattr(app, 'mqtt_initialized'):
        threading.Thread(target=setup_mqtt, daemon=True).start()
        logger.info("Flask应用初始化完成，MQTT客户端已启动")
        app.mqtt_initialized = True

# 执行命令
def execute_raspberry_command(command, timeout=10):
    if not mqtt_connected:
        return "错误: MQTT服务器未连接，无法发送命令"
        
    command_id = str(uuid.uuid4())
    payload = {
        "command_id": command_id,
        "command": command,
        "timeout": timeout
    }
    
    # 初始化结果
    results[command_id] = None
    
    # 发送命令
    logger.info(f"发送命令 [{command}] 到 {device_id}, ID: {command_id}")
    client.publish(f"device/{device_id}/command", json.dumps(payload, ensure_ascii=False))
    
    # 等待结果
    start_time = time.time()
    while time.time() - start_time < timeout + 2:  # 额外2秒等待时间
        if results[command_id] is not None:
            result = results[command_id]
            del results[command_id]  # 清理
            
            # 记录命令结果到InfluxDB
            if data_manager_available:
                success = result.get("success", False)
                output = result.get("output", "")
                error = result.get("error", "")
                
                try:
                    data_manager.write_command_result(
                        device_id=device_id,
                        command=command,
                        success=success,
                        output=output,
                        error=error
                    )
                except Exception as db_error:
                    logger.error(f"写入命令结果到InfluxDB失败: {db_error}")
            
            if result.get("success", False):
                return result.get("output", "")
            else:
                return f"错误: {result.get('error', '未知错误')}"
        time.sleep(0.1)
    
    # 超时
    logger.warning(f"命令 {command_id} 执行超时")
    del results[command_id]  # 清理
    
    # 记录超时到InfluxDB
    if data_manager_available:
        try:
            data_manager.write_command_result(
                device_id=device_id,
                command=command,
                success=False,
                error="命令执行超时，未收到响应"
            )
        except Exception as db_error:
            logger.error(f"写入超时记录到InfluxDB失败: {db_error}")
    
    return "命令执行超时，未收到响应"

# LangChain工具
@tool
def execute_command(command: str) -> str:
    """在树莓派上执行命令并返回结果"""
    return execute_raspberry_command(command)

# 创建LangChain代理
def get_agent():
    # 创建LLM
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        logger.info(f"API密钥状态: {'已设置' if api_key else '未设置'}")
        if not api_key:
            logger.error("未设置OpenAI API密钥")
            return None
        
        # 使用环境变量中指定的模型或默认模型
        model_name = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        logger.info(f"使用模型: {model_name}")
            
        # 简单测试API密钥
        logger.info(f"尝试使用API密钥创建ChatOpenAI对象")
        try:
            llm = ChatOpenAI(
                temperature=0, 
                verbose=True,
                model=model_name
            )
            # 测试API连接
            logger.info("测试API连接...")
            test_response = llm.invoke("测试连接，请回复'连接成功'")
            logger.info(f"API测试响应: {test_response}")
        except Exception as api_error:
            logger.error(f"API连接测试失败: {api_error}")
            logger.error(f"错误类型: {type(api_error).__name__}")
            return None
        
        # 创建工具
        tools = [execute_command]
        
        # 使用简单的方式创建代理
        logger.info("创建OpenAI函数代理...")
        try:
            # 使用简单方式创建代理
            system_message = """你是一个帮助用户执行树莓派Linux命令的AI助手。
用户会用自然语言告诉你他们想在树莓派上执行什么操作，你需要将其转换为适当的Linux命令。

遵循以下指南:
1. 只使用标准Linux命令
2. 确保命令安全，不要执行危险操作
3. 提供清晰的解释和命令执行结果
4. 如果你不确定某个命令是否安全，请选择更安全的替代方案
5. 所有响应都必须用中文回复
"""
            # 使用标准的create_openai_functions_agent函数
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_message),
                ("human", "{input}"),
                ("ai", "{agent_scratchpad}")
            ])
            
            # 使用最新的LangChain API创建代理
            from langchain.agents import create_openai_functions_agent
            from langchain.agents import AgentExecutor
            
            agent = create_openai_functions_agent(llm, tools, prompt)
            logger.info("代理创建成功")
            return AgentExecutor(agent=agent, tools=tools, verbose=True)
        except Exception as agent_error:
            logger.error(f"使用标准方式创建代理失败: {agent_error}")
            logger.error(f"错误类型: {type(agent_error).__name__}")
            
            # 尝试备用创建方式
            try:
                from langchain.agents import initialize_agent
                from langchain.agents.agent_types import AgentType
                logger.info("尝试使用备用方式创建代理...")
                agent_chain = initialize_agent(
                    tools,
                    llm,
                    agent=AgentType.OPENAI_FUNCTIONS,
                    verbose=True
                )
                logger.info("备用代理创建成功")
                return agent_chain
            except Exception as backup_error:
                logger.error(f"备用代理创建失败: {backup_error}")
                raise
    except Exception as e:
        logger.error(f"创建代理错误: {e}")
        logger.error(f"错误类型: {type(e).__name__}")
        import traceback
        logger.error(f"错误详情: {traceback.format_exc()}")
        return None

# 路由
@app.route('/')
def index():
    """首页"""
    # 获取Grafana URL及当前设备ID
    grafana_url = os.getenv("GRAFANA_URL", "http://localhost:3000")
    current_device_id = device_id
    
    # 尝试加载可用的仪表盘
    dashboard_options_js = "[]"
    dashboard_js = ""
    
    try:
        if dashboard_manager_available:
            # 获取仪表盘列表
            dashboards = dashboard_manager.get_dashboard_list()
            if dashboards:
                # 构建仪表盘选项的JavaScript数组
                dashboard_options_js = json.dumps(dashboards)
                logger.info(f"加载了 {len(dashboards)} 个仪表盘")
            else:
                logger.warning("没有可用的仪表盘")
    except Exception as e:
        logger.error(f"加载仪表盘出错: {e}")
        
    # 构建仪表盘JavaScript函数
    dashboard_js = """
    // 加载仪表盘列表
    function loadDashboards() {
        const dashboardSelect = document.getElementById('dashboard-select');
        const statusDiv = document.getElementById('dashboard-status');
        const iframe = document.getElementById('grafana-iframe');
        const placeholder = document.getElementById('dashboard-placeholder');
        
        // 清空现有选项
        dashboardSelect.innerHTML = '<option value="">-- 选择仪表盘 --</option>';
        
        // 先显示加载中状态
        statusDiv.textContent = '正在加载仪表盘列表...';
        statusDiv.className = 'alert-info';
        statusDiv.style.display = 'block';
        placeholder.style.display = 'none';
        
        // 从API获取最新的仪表盘列表
        fetch('/grafana/dashboards')
            .then(response => response.json())
            .then(data => {
                if (data.dashboards && data.dashboards.length > 0) {
                    // 更新全局变量
                    window.availableDashboards = data.dashboards;
                    
                    // 添加仪表盘选项
                    data.dashboards.forEach(dashboard => {
                        const option = document.createElement('option');
                        option.value = dashboard.uid;
                        option.textContent = dashboard.title;
                        dashboardSelect.appendChild(option);
                    });
                    
                    // 显示选择器
                    dashboardSelect.style.display = 'block';
                    statusDiv.style.display = 'none';
                    placeholder.style.display = 'block';
                    iframe.style.display = 'none';
                    
                    console.log('成功加载了', data.dashboards.length, '个仪表盘');
                } else {
                    // 没有可用的仪表盘
                    window.availableDashboards = [];
                    statusDiv.textContent = '没有可用的仪表盘。请检查Grafana服务是否运行并配置正确。';
                    statusDiv.className = 'alert-warning';
                    statusDiv.style.display = 'block';
                    placeholder.style.display = 'none';
                    dashboardSelect.style.display = 'none';
                    iframe.style.display = 'none';
                    
                    console.log('没有找到可用的仪表盘');
                }
            })
            .catch(error => {
                console.error('获取仪表盘列表出错:', error);
                statusDiv.textContent = `获取仪表盘列表出错: ${error.message}`;
                statusDiv.className = 'alert-error';
                statusDiv.style.display = 'block';
                placeholder.style.display = 'none';
                dashboardSelect.style.display = 'none';
                iframe.style.display = 'none';
            });
    }
    
    // 切换仪表盘
    function changeDashboard() {
        const dashboardSelect = document.getElementById('dashboard-select');
        const statusDiv = document.getElementById('dashboard-status');
        const iframe = document.getElementById('grafana-iframe');
        const placeholder = document.getElementById('dashboard-placeholder');
        
        const selectedUid = dashboardSelect.value;
        
        if (!selectedUid) {
            // 未选择仪表盘
            placeholder.style.display = 'block';
            iframe.style.display = 'none';
            statusDiv.style.display = 'none';
            return;
        }
        
        // 显示加载状态
        statusDiv.textContent = '正在加载仪表盘...';
        statusDiv.className = 'alert-info';
        statusDiv.style.display = 'block';
        placeholder.style.display = 'none';
        
        // 使用代理加载仪表盘
        iframe.src = `/grafana/view/${selectedUid}?device_id=${deviceId}`;
        iframe.style.display = 'block';
        statusDiv.style.display = 'none';
    }
    
    // 页面加载完成后初始化仪表盘
    document.addEventListener('DOMContentLoaded', function() {
        // 初始加载仪表盘列表
        loadDashboards();
        
        // 绑定刷新仪表盘按钮事件
        document.getElementById('refresh-dashboards').addEventListener('click', function() {
            // 导入仪表盘并刷新列表
            statusDiv = document.getElementById('dashboard-status');
            statusDiv.textContent = '正在导入仪表盘...';
            statusDiv.className = 'alert-info';
            statusDiv.style.display = 'block';
            
            // 先导入仪表盘
            fetch('/grafana/import', {
                method: 'POST'
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        statusDiv.textContent = '仪表盘导入成功，正在刷新列表...';
                        // 导入成功后刷新列表
                        setTimeout(() => {
                            loadDashboards();
                            alert(`导入成功！已导入 ${data.count} 个仪表盘。`);
                        }, 1000);
                    } else {
                        statusDiv.textContent = '仪表盘导入失败: ' + (data.message || '未知错误');
                        statusDiv.className = 'alert-error';
                        alert('导入仪表盘失败: ' + (data.message || '未知错误'));
                    }
                })
                .catch(error => {
                    console.error('导入仪表盘出错:', error);
                    statusDiv.textContent = `导入仪表盘出错: ${error.message}`;
                    statusDiv.className = 'alert-error';
                    alert('导入仪表盘出错: ' + error.message);
                });
        });
        
        // 为标签页绑定切换事件
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', () => {
                // 移除所有活动标签
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                
                // 激活当前标签
                tab.classList.add('active');
                const tabId = tab.getAttribute('data-tab');
                document.getElementById(`${tabId}-tab`).classList.add('active');
                
                // 特殊处理仪表盘
                if (tabId === 'dashboard') {
                    loadDashboards();
                }
            });
        });
    });
    """
    
    # HTML模板
    html_template = f'''
    <!DOCTYPE html>
    <html lang="zh">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>树莓派AI控制中心</title>
        <style>
            body {{
                font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f5f5;
                color: #333;
            }}
            h1 {{ color: #2c3e50; }}
            .container {{ display: flex; flex-direction: column; gap: 20px; }}
            textarea {{ width: 100%; height: 100px; margin: 10px 0; padding: 10px; border-radius: 5px; border: 1px solid #ddd; }}
            button {{ background: #3498db; color: white; border: none; padding: 10px 20px; cursor: pointer; border-radius: 5px; }}
            button:hover {{ background: #2980b9; }}
            #result {{ margin-top: 20px; padding: 15px; border: 1px solid #ddd; min-height: 150px; border-radius: 5px; white-space: pre-wrap; background: #f9f9f9; }}
            .loader {{ border: 4px solid #f3f3f3; border-top: 4px solid #3498db; border-radius: 50%; width: 20px; height: 20px; animation: spin 2s linear infinite; display: none; margin-left: 10px; }}
            @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
            .command-examples {{ background: #ecf0f1; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            .command-examples h3 {{ margin-top: 0; }}
            .flex-row {{ display: flex; align-items: center; }}
            .status {{ margin-top: 20px; padding: 10px; background: #e8f4fc; border-radius: 5px; }}
            footer {{ margin-top: 30px; text-align: center; color: #7f8c8d; font-size: 0.9em; }}
            .tabs {{ display: flex; margin-top: 20px; border-bottom: 1px solid #ddd; }}
            .tab {{ padding: 10px 20px; cursor: pointer; background: #f8f9fa; margin-right: 5px; border-radius: 5px 5px 0 0; }}
            .tab.active {{ background: #3498db; color: white; }}
            .tab-content {{ display: none; padding: 20px; border: 1px solid #ddd; border-top: none; min-height: 300px; }}
            .tab-content.active {{ display: block; }}
            iframe {{ width: 100%; height: 600px; border: none; }}
            .dashboard-selector {{ margin: 10px 0; }}
            .dashboard-selector select {{ padding: 5px; border-radius: 3px; }}
            .alert-info {{ background-color: #d1ecf1; color: #0c5460; padding: 10px; border-radius: 4px; margin-bottom: 10px; }}
            .alert-warning {{ background-color: #fff3cd; color: #856404; padding: 10px; border-radius: 4px; margin-bottom: 10px; }}
            .alert-error {{ background-color: #f8d7da; color: #721c24; padding: 10px; border-radius: 4px; margin-bottom: 10px; }}
            .alert-critical {{ background-color: #dc3545; color: white; padding: 10px; border-radius: 4px; margin-bottom: 10px; }}
            .settings-container {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
            .settings-section {{ padding: 15px; background: #f8f9fa; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <h1>树莓派AI控制中心</h1>
        <div class="status" id="status">状态: 检查连接中...</div>
        
        <div class="tabs">
            <div class="tab active" data-tab="command">命令控制</div>
            <div class="tab" data-tab="dashboard">数据仪表盘</div>
            <div class="tab" data-tab="devices">设备管理</div>
            <div class="tab" data-tab="alerts">告警信息</div>
            <div class="tab" data-tab="settings">系统设置</div>
        </div>
        
        <div class="tab-content active" id="command-tab">
            <div class="container">
                <div>
                    <h2>命令输入</h2>
                    <textarea id="command" placeholder="请描述您想在树莓派上执行的操作...例如：'查看系统运行状态' 或 '列出根目录下的文件'"></textarea>
                    <div class="flex-row">
                        <button id="execute">执行</button>
                        <div class="loader" id="loader"></div>
                    </div>
                </div>
                
                <div class="command-examples">
                    <h3>常用命令示例</h3>
                    <ul>
                        <li><strong>系统信息</strong>: 查看系统运行状态和资源使用情况</li>
                        <li><strong>温度监控</strong>: 检查CPU温度</li>
                        <li><strong>存储空间</strong>: 查看磁盘使用情况</li>
                        <li><strong>网络信息</strong>: 显示网络连接和IP配置</li>
                        <li><strong>进程列表</strong>: 查看正在运行的进程</li>
                    </ul>
                </div>
                
                <div>
                    <h2>执行结果</h2>
                    <pre id="result">在上方输入命令并点击"执行"按钮...</pre>
                </div>
            </div>
        </div>
        
        <div class="tab-content" id="dashboard-tab">
            <h2>设备数据仪表盘</h2>
            <div class="dashboard-selector">
                <label for="dashboard-select">选择仪表盘:</label>
                <select id="dashboard-select" onchange="changeDashboard()"></select>
            </div>
            <div id="grafana-embed">
                <div id="dashboard-status" class="alert-info" style="padding: 10px; margin-bottom: 15px; display: none;"></div>
                <iframe id="grafana-iframe" src="" allowfullscreen style="display: none;"></iframe>
                <div id="dashboard-placeholder">
                    <p>请选择一个仪表盘查看数据。如果没有可用的仪表盘，请确保Grafana服务已启动并配置正确。</p>
                </div>
            </div>
        </div>
        
        <div class="tab-content" id="devices-tab">
            <h2>设备管理</h2>
            <div id="devices-container">
                <iframe id="devices-iframe" src="/devices" style="width:100%; height:800px; border:none;"></iframe>
            </div>
        </div>
        
        <div class="tab-content" id="alerts-tab">
            <h2>告警信息</h2>
            <div id="alerts-container">
                <p>正在加载告警信息...</p>
            </div>
        </div>
        
        <div class="tab-content" id="settings-tab">
            <h2>系统设置</h2>
            <div class="settings-container">
                <div class="settings-section">
                    <h3>InfluxDB连接</h3>
                    <div id="influxdb-info">
                        <p>正在加载InfluxDB信息...</p>
                    </div>
                </div>
                
                <div class="settings-section">
                    <h3>设备配置</h3>
                    <div>
                        <label for="device-id">设备ID:</label>
                        <input type="text" id="device-id" value="" disabled>
                    </div>
                    <div style="margin-top: 15px;">
                        <button id="refresh-dashboards">刷新仪表盘列表</button>
                    </div>
                </div>
            </div>
        </div>
        
        <footer>
            树莓派AI控制系统 &copy; 2024
        </footer>
        
        <script>
            // 全局变量
            const grafanaUrl = "{grafana_url}";
            const deviceId = "{current_device_id}";
            const availableDashboards = {dashboard_options_js};
            
            // 仪表盘处理函数
            {dashboard_js}
            
            // 检查MQTT连接状态
            function checkStatus() {{
                fetch('/status')
                    .then(response => response.json())
                    .then(data => {{
                        document.getElementById('status').textContent = `状态: ${{data.status}}`;
                        document.getElementById('status').style.background = data.connected ? '#d4edda' : '#f8d7da';
                        
                        // 更新设备ID
                        document.getElementById('device-id').value = data.device_id;
                    }})
                    .catch(error => {{
                        document.getElementById('status').textContent = `状态: 连接错误 - ${{error.message}}`;
                        document.getElementById('status').style.background = '#f8d7da';
                    }});
            }}
            
            // 定期检查状态
            checkStatus();
            setInterval(checkStatus, 10000);
            
            // 执行命令
            document.getElementById('execute').addEventListener('click', async () => {{
                const command = document.getElementById('command').value;
                if (!command) return;
                
                // 显示加载中
                document.getElementById('loader').style.display = 'inline-block';
                document.getElementById('result').textContent = '正在处理...';
                document.getElementById('execute').disabled = true;
                
                try {{
                    const response = await fetch('/execute', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json',
                        }},
                        body: JSON.stringify({{ command }}),
                    }});
                    
                    const data = await response.json();
                    document.getElementById('result').textContent = data.result;
                }} catch (error) {{
                    document.getElementById('result').textContent = `错误: ${{error.message}}`;
                }} finally {{
                    document.getElementById('loader').style.display = 'none';
                    document.getElementById('execute').disabled = false;
                }}
            }});
        </script>
    </body>
    </html>
    '''
    
    return html_template

@app.route('/devices')
def devices_page():
    """设备管理页面"""
    try:
        with open(os.path.join(os.path.dirname(__file__), 'templates/devices.html'), 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"加载设备管理页面出错: {e}")
        return "<h1>设备管理页面加载失败</h1><p>请检查日志获取详细错误信息</p>"

@app.route('/status')
def status():
    # 检查MQTT连接状态
    return jsonify({
        "connected": mqtt_connected,
        "status": "已连接到MQTT服务器" if mqtt_connected else "未连接到MQTT服务器",
        "device_id": device_id,
        "mqtt_host": mqtt_host
    })

@app.route('/execute', methods=['POST'])
def execute():
    try:
        data = request.get_json()
        command = data.get('command', '')
        
        if not command:
            return jsonify({"result": "错误: 命令不能为空"})
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return jsonify({"result": "错误: 未设置OpenAI API密钥环境变量。请在.env文件中设置OPENAI_API_KEY=sk-您的密钥"})
        
        # 重新设置环境变量，确保API客户端能正确获取
        os.environ["OPENAI_API_KEY"] = api_key
        
        agent_executor = get_agent()
        if agent_executor is None:
            return jsonify({"result": "错误: 无法创建AI代理，请检查日志以获取详细错误信息"})
            
        response = agent_executor.invoke({"input": command})
        
        return jsonify({"result": response["output"]})
    except Exception as e:
        logger.error(f"执行命令错误: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        return jsonify({"result": f"错误: {str(e)}"})

# 添加路由列表路由
@app.route('/debug/routes')
def list_routes():
    """列出所有注册的路由"""
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            "endpoint": rule.endpoint,
            "methods": list(rule.methods),
            "path": str(rule)
        })
    return jsonify({"routes": routes})

def setup_routes(app):
    """将所有路由添加到应用中"""
    # 添加主页路由
    @app.route('/')
    def index():
        """首页"""
        return index_original()
        
    # 添加状态路由
    @app.route('/status')
    def status_route():
        """状态信息"""
        return status()
        
    # 添加执行命令路由
    @app.route('/execute', methods=['POST'])
    def execute_route():
        """执行命令"""
        return execute()
        
    # 添加设备管理页面路由
    @app.route('/devices')
    def devices_ui():
        """设备管理页面"""
        return devices_page()

# 将原始函数重命名为index_original
index_original = index

# 主函数
if __name__ == '__main__':
    # 确保我们在app.run之前初始化MQTT
    setup_mqtt()
    app.run(debug=True, host='0.0.0.0', port=5000) 
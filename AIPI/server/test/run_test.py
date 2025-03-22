#!/usr/bin/env python3
import json
import uuid
import time
import paho.mqtt.client as mqtt

# 配置
mqtt_host = "localhost"
device_id = "rpi_001"
commands = [
    "hostname",
    "uptime",
    "free -h",
    "df -h",
    "cat /proc/cpuinfo | grep Model",
    "ifconfig || ip addr"
]

results = {}
result_received = False

# MQTT回调函数
def on_connect(client, userdata, flags, rc):
    print(f"已连接到MQTT代理：{rc}")
    client.subscribe(f"device/{device_id}/result")

def on_message(client, userdata, msg):
    global result_received
    try:
        data = json.loads(msg.payload)
        command_id = data.get("command_id")
        if command_id in results:
            results[command_id] = data
            result_received = True
            print(f"收到命令 {command_id} 的结果")
    except Exception as e:
        print(f"处理消息出错: {e}")

# 创建MQTT客户端
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

# 连接到MQTT服务器
client.connect(mqtt_host, 1883, 60)
client.loop_start()

# 运行测试
for command in commands:
    # 重置标志
    result_received = False
    
    # 生成命令ID
    command_id = str(uuid.uuid4())
    results[command_id] = None
    
    # 创建命令负载
    payload = {
        "command_id": command_id,
        "command": command,
        "timeout": 10
    }
    
    # 发送命令
    print(f"\n[测试] 发送命令: {command}")
    client.publish(f"device/{device_id}/command", json.dumps(payload))
    
    # 等待结果
    start_time = time.time()
    while time.time() - start_time < 10 and not result_received:
        time.sleep(0.1)
    
    # 显示结果
    if result_received:
        result = results[command_id]
        print(f"结果: {'成功' if result.get('success') else '失败'}")
        print(f"输出:\n{result.get('output', '').strip()}")
        if result.get('error'):
            print(f"错误:\n{result.get('error')}")
    else:
        print(f"超时: 未收到结果")
    
    # 等待一小段时间再发送下一个命令
    time.sleep(1)

# 清理
client.loop_stop()
client.disconnect()
print("\n测试完成!")

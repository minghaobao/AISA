# 创建测试脚本
#!/usr/bin/env python3
import json
import uuid
import time
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish

# 配置
mqtt_host = "localhost"  # PC上的MQTT服务器
device_id = "rpi_001"
command = "uname -a"  # 示例Linux命令

# MQTT回调函数
def on_connect(client, userdata, flags, rc):
    print(f"已连接到MQTT代理：{rc}")
    client.subscribe(f"device/{device_id}/result")
    client.subscribe(f"device/{device_id}/status")

def on_message(client, userdata, msg):
    print(f"收到消息：{msg.topic}")
    try:
        data = json.loads(msg.payload)
        if "status" in data:
            print(f"设备状态: {data['status']}")
            if "system_info" in data:
                print(f"系统信息: {json.dumps(data['system_info'], indent=2, ensure_ascii=False)}")
        else:
            print(f"命令结果:")
            print(f"成功: {'✓' if data.get('success') else '✗'}")
            print(f"输出:\n{data.get('output', '')}")
            if data.get('error'):
                print(f"错误:\n{data.get('error')}")
    except Exception as e:
        print(f"处理消息出错: {e}")
        print(f"原始消息: {msg.payload.decode()}")

# 创建MQTT客户端
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

# 连接到MQTT服务器
client.connect(mqtt_host, 1883, 60)
client.loop_start()

# 发送测试命令
command_id = str(uuid.uuid4())
payload = {
    "command_id": command_id,
    "command": command,
    "timeout": 10
}

print(f"发送命令到 {device_id}: {command}")
client.publish(f"device/{device_id}/command", json.dumps(payload))

# 等待结果
try:
    time.sleep(10)  # 等待足够时间接收结果
except KeyboardInterrupt:
    print("程序被用户中断")
finally:
    client.loop_stop()
    client.disconnect()

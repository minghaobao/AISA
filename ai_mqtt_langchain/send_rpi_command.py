#!/usr/bin/env python3
import os
import sys
import json
import time
import uuid
import argparse
import paho.mqtt.client as mqtt
from datetime import datetime

# 命令结果存储
command_results = {}
result_received = False

def on_connect(client, userdata, flags, rc):
    """连接回调函数"""
    if rc == 0:
        print(f"已连接到MQTT代理服务器")
        
        # 订阅结果主题
        device_id = userdata.get('device_id')
        result_topic = f"device/{device_id}/result"
        client.subscribe(result_topic)
        print(f"已订阅结果主题: {result_topic}")
        
        # 订阅状态主题
        status_topic = f"device/{device_id}/status"
        client.subscribe(status_topic)
        print(f"已订阅状态主题: {status_topic}")
    else:
        print(f"连接MQTT代理服务器失败，返回码: {rc}")
        sys.exit(1)

def on_message(client, userdata, msg):
    """消息回调函数"""
    global result_received
    
    topic = msg.topic
    payload = msg.payload.decode('utf-8')
    
    try:
        data = json.loads(payload)
        
        # 处理结果消息
        if topic == f"device/{userdata.get('device_id')}/result":
            command_id = data.get('command_id')
            if command_id:
                command_results[command_id] = data
                
                # 打印结果
                if data.get('success'):
                    print("\n命令执行成功！")
                else:
                    print("\n命令执行失败！")
                
                print(f"设备ID: {data.get('device_id')}")
                print(f"命令ID: {command_id}")
                print(f"执行时间: {data.get('timestamp')}")
                
                # 打印输出
                output = data.get('output', '')
                if output:
                    print("\n输出:")
                    print("-" * 40)
                    print(output)
                    print("-" * 40)
                
                # 打印错误
                error = data.get('error', '')
                if error:
                    print("\n错误:")
                    print("-" * 40)
                    print(error)
                    print("-" * 40)
                
                result_received = True
                
        # 处理状态消息
        elif topic == f"device/{userdata.get('device_id')}/status":
            status = data.get('status')
            timestamp = data.get('timestamp')
            print(f"设备状态更新: {status} (时间: {timestamp})")
            
    except json.JSONDecodeError:
        print(f"无法解析消息为JSON: {payload}")
    except Exception as e:
        print(f"处理消息时出错: {e}")

def send_command(args):
    """发送命令到树莓派"""
    # 生成命令ID
    command_id = str(uuid.uuid4())
    
    # 准备命令消息
    command_data = {
        "command_id": command_id,
        "command": args.command,
        "timeout": args.timeout
    }
    
    # 创建MQTT客户端
    client_id = f"sender_{int(time.time())}"
    client = mqtt.Client(client_id=client_id, userdata={"device_id": args.device_id})
    
    # 设置回调函数
    client.on_connect = on_connect
    client.on_message = on_message
    
    # 设置认证信息
    if args.mqtt_username and args.mqtt_password:
        client.username_pw_set(args.mqtt_username, args.mqtt_password)
    
    try:
        # 连接MQTT代理服务器
        print(f"正在连接到MQTT代理服务器 {args.mqtt_host}:{args.mqtt_port}...")
        client.connect(args.mqtt_host, args.mqtt_port, keepalive=60)
        client.loop_start()
        
        # 等待连接
        time.sleep(1)
        
        # 发送命令
        command_topic = f"device/{args.device_id}/command"
        print(f"正在发送命令到 {args.device_id}: {args.command}")
        client.publish(command_topic, json.dumps(command_data))
        
        # 等待结果
        start_time = time.time()
        while time.time() - start_time < args.wait_time and not result_received:
            time.sleep(0.1)
            print(".", end="", flush=True)
            
        if not result_received:
            print("\n等待结果超时！")
            
        # 断开连接
        client.loop_stop()
        client.disconnect()
        
    except KeyboardInterrupt:
        print("\n操作被用户中断")
        client.loop_stop()
        client.disconnect()
    except Exception as e:
        print(f"发送命令时出错: {e}")
        client.loop_stop()
        try:
            client.disconnect()
        except:
            pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="向树莓派发送命令")
    parser.add_argument("--device-id", required=True, help="设备ID")
    parser.add_argument("--command", required=True, help="要执行的命令")
    parser.add_argument("--mqtt-host", default="localhost", help="MQTT代理服务器主机")
    parser.add_argument("--mqtt-port", type=int, default=1883, help="MQTT代理服务器端口")
    parser.add_argument("--mqtt-username", help="MQTT用户名")
    parser.add_argument("--mqtt-password", help="MQTT密码")
    parser.add_argument("--timeout", type=int, default=60, help="命令超时时间（秒）")
    parser.add_argument("--wait-time", type=int, default=30, help="等待结果时间（秒）")
    
    args = parser.parse_args()
    
    # 发送命令
    send_command(args) 
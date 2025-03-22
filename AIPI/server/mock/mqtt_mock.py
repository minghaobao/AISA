#!/usr/bin/env python3
import os
import time
import json
import threading
import datetime

class MQTTMockService:
    def __init__(self):
        self.running = True
        self.device_data = {
            "rpi_001": {
                "temperature": 25.5,
                "humidity": 45.0,
                "cpu_load": 15.2,
                "status": "online"
            },
            "rpi_002": {
                "temperature": 26.8,
                "humidity": 50.2,
                "cpu_load": 22.4,
                "status": "online"
            }
        }
        
    def start(self):
        print("MQTT模拟服务启动")
        self.data_thread = threading.Thread(target=self.generate_mock_data)
        self.data_thread.daemon = True
        self.data_thread.start()
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.running = False
            print("MQTT模拟服务停止")
    
    def generate_mock_data(self):
        while self.running:
            # 模拟数据变化
            for device_id in self.device_data:
                self.device_data[device_id]["temperature"] += (0.5 - (1.0 * (time.time() % 10) / 10))
                self.device_data[device_id]["humidity"] += (0.3 - (0.6 * (time.time() % 8) / 8))
                self.device_data[device_id]["cpu_load"] = 10 + (30 * abs(time.time() % 20 - 10) / 10)
                
                # 输出到控制台，模拟MQTT消息
                print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 设备 {device_id} 数据: {json.dumps(self.device_data[device_id])}")
                
                # 写入到文件，模拟数据存储
                with open(f"{device_id}_data.json", "w") as f:
                    f.write(json.dumps(self.device_data[device_id], indent=2))
            
            time.sleep(5)  # 每5秒更新一次

if __name__ == "__main__":
    service = MQTTMockService()
    service.start()

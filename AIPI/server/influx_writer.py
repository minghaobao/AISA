import logging
import time
from datetime import datetime
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from config import INFLUXDB_CONFIG, LOG_CONFIG

# 配置日志
logging.basicConfig(
    level=LOG_CONFIG["level"],
    format=LOG_CONFIG["format"],
    filename=LOG_CONFIG.get("filename")
)
logger = logging.getLogger("influx_writer")

# InfluxDB客户端初始化
try:
    influx_client = InfluxDBClient(
        url=INFLUXDB_CONFIG["url"],
        token=INFLUXDB_CONFIG["token"],
        org=INFLUXDB_CONFIG["org"]
    )
    write_api = influx_client.write_api(write_options=SYNCHRONOUS)
    logger.info("InfluxDB客户端初始化成功")
    INFLUX_CONNECTED = True
except Exception as e:
    logger.error(f"InfluxDB客户端初始化失败: {str(e)}")
    INFLUX_CONNECTED = False

def write_to_influxdb(device_id, data):
    """
    将设备数据写入InfluxDB
    :param device_id: 设备ID
    :param data: 设备数据字典
    :return: 是否写入成功
    """
    if not INFLUX_CONNECTED:
        logger.warning("InfluxDB未连接，无法写入数据")
        return False
    
    try:
        # 创建数据点
        point = Point(INFLUXDB_CONFIG["measurement"])
        
        # 添加标签
        point.tag("device_id", device_id)
        
        # 如果数据中包含设备类型，也添加为标签
        if "device_type" in data:
            point.tag("device_type", data["device_type"])
            
        # 如果数据中包含位置信息，添加为标签
        if "location" in data:
            point.tag("location", data["location"])
            
        # 添加字段（测量值）
        for key, value in data.items():
            # 跳过不作为字段的键
            if key in ["device_id", "device_type", "location", "timestamp"]:
                continue
                
            # 根据数据类型添加字段
            if isinstance(value, (int, float)):
                point.field(key, value)
            elif isinstance(value, bool):
                point.field(key, 1 if value else 0)
            else:
                point.field(key, str(value))
                
        # 添加时间戳
        timestamp = data.get("timestamp")
        if timestamp:
            if isinstance(timestamp, (int, float)):
                # 将Unix时间戳转换为纳秒精度
                point.time(int(timestamp * 1_000_000_000), WritePrecision.NS)
            elif isinstance(timestamp, str):
                # 尝试解析字符串时间戳
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    point.time(int(dt.timestamp() * 1_000_000_000), WritePrecision.NS)
                except ValueError:
                    # 使用当前时间
                    point.time(datetime.utcnow())
        else:
            # 使用当前时间
            point.time(datetime.utcnow())
            
        # 写入数据
        write_api.write(
            bucket=INFLUXDB_CONFIG["bucket"],
            org=INFLUXDB_CONFIG["org"],
            record=point
        )
        
        logger.debug(f"成功写入设备 {device_id} 数据到InfluxDB")
        return True
        
    except Exception as e:
        logger.error(f"写入数据到InfluxDB时出错: {str(e)}")
        return False

def write_event_to_influxdb(event_type, device_id, description, severity="info"):
    """
    写入事件数据到InfluxDB
    :param event_type: 事件类型
    :param device_id: 设备ID
    :param description: 事件描述
    :param severity: 事件严重性
    :return: 是否写入成功
    """
    if not INFLUX_CONNECTED:
        logger.warning("InfluxDB未连接，无法写入事件数据")
        return False
    
    try:
        # 创建事件数据点
        point = Point("events")
        
        # 添加标签
        point.tag("device_id", device_id)
        point.tag("event_type", event_type)
        point.tag("severity", severity)
        
        # 添加字段
        point.field("description", description)
        
        # 使用当前时间
        point.time(datetime.utcnow())
        
        # 写入数据
        write_api.write(
            bucket=INFLUXDB_CONFIG["bucket"],
            org=INFLUXDB_CONFIG["org"],
            record=point
        )
        
        logger.info(f"成功写入事件数据到InfluxDB: {event_type} - {description}")
        return True
        
    except Exception as e:
        logger.error(f"写入事件数据到InfluxDB时出错: {str(e)}")
        return False

def query_latest_data(device_id, fields=None, time_range="1h"):
    """
    查询设备最新数据
    :param device_id: 设备ID
    :param fields: 要查询的字段列表
    :param time_range: 时间范围（例如：1h, 1d）
    :return: 查询结果
    """
    if not INFLUX_CONNECTED:
        logger.warning("InfluxDB未连接，无法查询数据")
        return None
    
    try:
        query_api = influx_client.query_api()
        
        fields_clause = "*"
        if fields:
            fields_clause = ", ".join([f'r["{field}"]' for field in fields])
        
        query = f'''
        from(bucket: "{INFLUXDB_CONFIG["bucket"]}")
            |> range(start: -{time_range})
            |> filter(fn: (r) => r["_measurement"] == "{INFLUXDB_CONFIG["measurement"]}")
            |> filter(fn: (r) => r["device_id"] == "{device_id}")
            |> last()
        '''
        
        result = query_api.query(org=INFLUXDB_CONFIG["org"], query=query)
        
        # 处理结果
        data = {}
        for table in result:
            for record in table.records:
                field = record.get_field()
                value = record.get_value()
                data[field] = value
                
        return data
        
    except Exception as e:
        logger.error(f"查询InfluxDB数据时出错: {str(e)}")
        return None

def close_connection():
    """关闭InfluxDB连接"""
    if INFLUX_CONNECTED:
        influx_client.close()
        logger.info("InfluxDB连接已关闭")

if __name__ == "__main__":
    # 测试代码
    test_data = {
        "device_id": "temp_sensor_001",
        "temperature": 25.5,
        "humidity": 60,
        "battery": 95,
        "status": "normal",
        "timestamp": time.time()
    }
    
    result = write_to_influxdb("temp_sensor_001", test_data)
    print(f"写入数据结果: {result}")
    
    # 写入事件
    event_result = write_event_to_influxdb(
        "device_restart", 
        "temp_sensor_001", 
        "设备已重启",
        "info"
    )
    print(f"写入事件结果: {event_result}")
    
    # 查询最新数据
    latest_data = query_latest_data("temp_sensor_001")
    print(f"最新数据: {latest_data}")
    
    # 关闭连接
    close_connection() 
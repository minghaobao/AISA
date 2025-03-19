#!/bin/bash
# AI MQTT LangChain平台数据备份脚本

# 设置变量
BACKUP_DIR="./backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="aisa_backup_$DATE"
INFLUXDB_BACKUP="$BACKUP_DIR/influxdb_$DATE"
MQTT_BACKUP="$BACKUP_DIR/mqtt_$DATE"
GRAFANA_BACKUP="$BACKUP_DIR/grafana_$DATE"
LOG_BACKUP="$BACKUP_DIR/logs_$DATE"

# 创建备份目录
mkdir -p $BACKUP_DIR
mkdir -p $INFLUXDB_BACKUP
mkdir -p $MQTT_BACKUP
mkdir -p $GRAFANA_BACKUP
mkdir -p $LOG_BACKUP

echo "===== 开始备份 - $DATE ====="

# 备份InfluxDB数据
echo "- 备份InfluxDB数据..."
if [ "$(docker ps -q -f name=influxdb)" ]; then
    # 使用InfluxDB容器内部命令进行备份
    docker exec influxdb influx backup -t $INFLUXDB_TOKEN $INFLUXDB_BACKUP
    if [ $? -eq 0 ]; then
        echo "  InfluxDB备份成功"
    else
        echo "  InfluxDB备份失败"
    fi
else
    echo "  InfluxDB容器未运行，跳过备份"
fi

# 备份MQTT数据
echo "- 备份MQTT数据..."
if [ -d "./mosquitto/data" ]; then
    cp -r ./mosquitto/data $MQTT_BACKUP/
    echo "  MQTT数据备份成功"
else
    echo "  MQTT数据目录不存在，跳过备份"
fi

# 备份Grafana数据
echo "- 备份Grafana数据..."
if [ -d "./grafana/data" ]; then
    cp -r ./grafana/data $GRAFANA_BACKUP/
    echo "  Grafana数据备份成功"
else
    echo "  Grafana数据目录不存在，跳过备份"
fi

# 备份日志文件
echo "- 备份日志文件..."
if [ -d "./logs" ]; then
    cp -r ./logs $LOG_BACKUP/
    echo "  日志备份成功"
else
    echo "  日志目录不存在，跳过备份"
fi

# 压缩备份文件
echo "- 压缩备份文件..."
tar -czf "$BACKUP_DIR/$BACKUP_NAME.tar.gz" -C $BACKUP_DIR influxdb_$DATE mqtt_$DATE grafana_$DATE logs_$DATE
if [ $? -eq 0 ]; then
    echo "  备份文件压缩成功: $BACKUP_NAME.tar.gz"
    # 清理临时文件
    rm -rf $INFLUXDB_BACKUP $MQTT_BACKUP $GRAFANA_BACKUP $LOG_BACKUP
else
    echo "  备份文件压缩失败"
fi

# 保留最近10个备份，删除更早的备份
echo "- 清理旧备份..."
ls -t $BACKUP_DIR/*.tar.gz | tail -n +11 | xargs -r rm
echo "  保留最近10个备份，删除更早的备份"

echo "===== 备份完成 ====="

# 显示备份信息
echo "备份文件位置: $BACKUP_DIR/$BACKUP_NAME.tar.gz"
echo "备份大小: $(du -h $BACKUP_DIR/$BACKUP_NAME.tar.gz | cut -f1)"
echo "剩余备份文件:"
ls -lh $BACKUP_DIR/*.tar.gz 
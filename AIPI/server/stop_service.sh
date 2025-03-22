#!/bin/bash
# AISA服务停止脚本

# 设置变量
SERVER_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="${SERVER_DIR}/service.pid"

# 检查PID文件是否存在
if [ ! -f "$PID_FILE" ]; then
    echo "错误: 未找到PID文件，服务可能未启动。"
    exit 1
fi

# 读取PID
PID=$(cat "$PID_FILE")

# 检查PID是否为数字
if ! [[ "$PID" =~ ^[0-9]+$ ]]; then
    echo "错误: PID文件内容无效: $PID"
    exit 1
fi

# 检查进程是否存在
if ! ps -p "$PID" > /dev/null; then
    echo "警告: 进程ID $PID 不存在，服务可能已经停止。"
    rm -f "$PID_FILE"
    exit 0
fi

# 停止进程
echo "正在停止AISA服务 (PID: $PID)..."
kill "$PID"

# 等待进程结束
TIMEOUT=10
COUNT=0
while ps -p "$PID" > /dev/null && [ $COUNT -lt $TIMEOUT ]; do
    echo "等待服务停止..."
    sleep 1
    COUNT=$((COUNT + 1))
done

# 检查进程是否已经停止
if ps -p "$PID" > /dev/null; then
    echo "服务没有及时响应，尝试强制终止..."
    kill -9 "$PID"
    sleep 1
fi

# 删除PID文件
rm -f "$PID_FILE"

# 确认进程已经停止
if ! ps -p "$PID" > /dev/null; then
    echo "AISA服务已成功停止。"
    echo "$(date) - 停止AISA服务" >> "${SERVER_DIR}/service.log"
else
    echo "错误: 无法停止AISA服务 (PID: $PID)。请尝试手动终止进程。"
    exit 1
fi 
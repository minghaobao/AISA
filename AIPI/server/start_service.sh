#!/bin/bash
# AISA服务启动脚本

# 设置变量
SERVER_DIR="$(cd "$(dirname "$0")" && pwd)"
PORT=5000
MODEL="gpt-3.5-turbo"
LOG_FILE="${SERVER_DIR}/service.log"

# 解析命令行参数
while [[ $# -gt 0 ]]; do
  case $1 in
    --port)
      PORT="$2"
      shift 2
      ;;
    --model)
      MODEL="$2"
      shift 2
      ;;
    --debug)
      DEBUG="--debug"
      shift
      ;;
    --help)
      echo "使用方法: $0 [选项]"
      echo "选项:"
      echo "  --port PORT    指定服务端口 (默认: 5000)"
      echo "  --model MODEL  指定AI模型 (默认: gpt-3.5-turbo)"
      echo "  --debug        启用调试模式"
      echo "  --help         显示帮助信息"
      exit 0
      ;;
    *)
      echo "未知选项: $1"
      echo "使用 --help 查看帮助信息"
      exit 1
      ;;
  esac
done

# 显示启动信息
echo "正在启动AISA服务..."
echo "端口: $PORT"
echo "模型: $MODEL"
echo "调试模式: ${DEBUG:-否}"
echo "日志文件: $LOG_FILE"

# 检查Python版本
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到python3命令。请确保已安装Python 3." >&2
    exit 1
fi

# 进入服务器目录
cd "$SERVER_DIR" || { echo "错误: 无法进入服务器目录: $SERVER_DIR"; exit 1; }

# 启动服务
echo "$(date) - 启动AISA服务" >> "$LOG_FILE"
python3 integrated_server.py --port "$PORT" --model "$MODEL" --no-api-check $DEBUG >> "$LOG_FILE" 2>&1 &

# 存储PID
PID=$!
echo $PID > "${SERVER_DIR}/service.pid"
echo "服务已启动，进程ID: $PID"
echo "服务正在运行在: http://localhost:$PORT"
echo "可使用以下命令停止服务: kill $PID"
echo "或执行: kill \$(cat ${SERVER_DIR}/service.pid)" 
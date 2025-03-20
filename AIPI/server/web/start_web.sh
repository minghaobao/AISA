#!/bin/bash

# 设置颜色输出
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}启动树莓派AI命令控制中心Web界面...${NC}"

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}错误: 未找到Python3，请确保已安装Python3${NC}"
    exit 1
fi

# 进入脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# 检查是否已安装所需依赖
if ! python3 -c "import flask" &> /dev/null; then
    echo -e "${YELLOW}安装所需依赖...${NC}"
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo -e "${RED}错误: 安装依赖失败${NC}"
        exit 1
    fi
fi

# 启动Web服务器
echo -e "${GREEN}启动Web服务器...${NC}"
python3 start_web.py "$@"

if [ $? -ne 0 ]; then
    echo -e "${RED}错误: 启动Web服务器失败${NC}"
    exit 1
fi 
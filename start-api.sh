#!/bin/bash

# 设置脚本在出错时退出
set -e

# 定义日志文件
COMFYUI_LOG="$HOME/comfy-api/comfyui.log"
WEBAPI_LOG="$HOME/comfy-api/webapi.log"

# 设置默认的 host
WEBAPI_HOST=8.155.23.126

# 启动 ComfyUI (在后台运行，并将日志输出到文件)
python /Users/william/comfy-api/ComfyUI/main.py --force-fp16 --listen 0.0.0.0 >> "$COMFYUI_LOG" 2>&1 &

# 启动 webapi (并将日志输出到文件)
python /Users/william/comfy-api/webapi/api.py >> "$WEBAPI_LOG" 2>&1 &

echo "ComfyUI and webapi started in background. Check logs for details."

exit 0


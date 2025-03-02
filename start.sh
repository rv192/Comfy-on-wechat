#!/bin/bash
# 设置默认的 host 为 127.0.0.1
WEBAPI_HOST=${WEBAPI_HOST:-127.0.0.1}

# 使用 sed 命令替换 config.json 中的 host
sed -i "s/\"host\": \".*\"/\"host\": \"${WEBAPI_HOST}\"/g" /app/ComfyUI/webapi/config.json
python ./main.py --force-fp16 --listen 0.0.0.0 &
python ./webapi/api.py
wait

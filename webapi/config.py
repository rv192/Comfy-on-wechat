import json
import os

# 默认配置
DEFAULT_CONFIG = {
    "comfyui_srv": "127.0.0.1:8188",
    "webapi": {
        "host": "127.0.0.1",
        "port": 8008
    }
}

def load_config():
    """加载配置文件，如果配置项缺失则使用默认值"""
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            user_config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return DEFAULT_CONFIG

    # 使用默认值填充缺失的配置项
    config = DEFAULT_CONFIG.copy()
    
    # 更新 comfyui_srv
    if "comfyui_srv" in user_config:
        config["comfyui_srv"] = user_config["comfyui_srv"]
    
    # 更新 webapi 配置
    if "webapi" in user_config:
        config["webapi"].update(user_config["webapi"])
    
    return config 
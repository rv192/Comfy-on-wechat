import json
import os
from typing import Dict, Any

class Config:
    _instance = None
    _config: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._config:
            self.load_config()

    def load_config(self):
        """加载配置文件"""
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
        except FileNotFoundError:
            raise Exception(f"配置文件不存在: {config_path}")
        except json.JSONDecodeError:
            raise Exception(f"配置文件格式错误: {config_path}")

    @property
    def comfyui_server(self) -> str:
        """获取 ComfyUI 服务器地址"""
        return self._config.get('comfyui', {}).get('server', '127.0.0.1:8188')

    @property
    def image_url_base(self) -> str:
        """获取图片基础 URL"""
        return self._config.get('comfyui', {}).get('image_url_base', 'http://127.0.0.1:8188')

    @property
    def server_host(self) -> str:
        """获取服务器主机地址"""
        return self._config.get('server', {}).get('host', '0.0.0.0')

    @property
    def server_port(self) -> int:
        """获取服务器端口"""
        return self._config.get('server', {}).get('port', 8000)

# 创建全局配置实例
config = Config() 
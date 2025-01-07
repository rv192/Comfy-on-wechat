from typing import Optional
from collections import deque
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json

@dataclass
class RequestRecord:
    """请求记录"""
    hash_key: str
    timestamp: datetime
    result: Optional[dict]

class RequestDeduplication:
    """请求去重处理器"""
    def __init__(self, max_size: int = 10, time_window: int = 90):
        """
        初始化请求去重处理器
        
        Args:
            max_size: 队列最大长度
            time_window: 时间窗口（秒）
        """
        self.queue = deque(maxlen=max_size)
        self.time_window = time_window
    
    def _generate_hash(self, workflow_name: str, prompt: str, width: int, height: int, urls: Optional[str]) -> str:
        """生成请求参数的哈希值"""
        params = {
            "workflow_name": workflow_name,
            "prompt": prompt,
            "width": width,
            "height": height,
            "urls": urls or ""
        }
        # 将参数转换为规范化的JSON字符串（确保相同的参数总是产生相同的字符串）
        param_str = json.dumps(params, sort_keys=True)
        return hashlib.md5(param_str.encode()).hexdigest()
    
    def check_request(self, workflow_name: str, prompt: str, width: int, height: int, 
                     urls: Optional[str]) -> Optional[dict]:
        """
        检查请求是否重复
        
        Args:
            workflow_name: 工作流名称
            prompt: 提示词
            width: 图片宽度
            height: 图片高度
            urls: 输入图片URL
            
        Returns:
            如果是重复请求且结果有效，返回之前的结果；否则返回None
        """
        current_time = datetime.now()
        hash_key = self._generate_hash(workflow_name, prompt, width, height, urls)
        
        # 检查是否有重复请求
        for record in self.queue:
            if record.hash_key == hash_key:
                time_diff = (current_time - record.timestamp).total_seconds()
                if time_diff <= self.time_window and record.result is not None:
                    return record.result
                # 如果找到记录但已过期或结果为空，更新时间戳
                record.timestamp = current_time
                return None
        
        # 如果没有找到记录，创建新记录
        self.queue.append(RequestRecord(
            hash_key=hash_key,
            timestamp=current_time,
            result=None
        ))
        
        return None
    
    def update_result(self, workflow_name: str, prompt: str, width: int, height: int, 
                     urls: Optional[str], result: dict) -> None:
        """
        更新请求的结果
        
        Args:
            workflow_name: 工作流名称
            prompt: 提示词
            width: 图片宽度
            height: 图片高度
            urls: 输入图片URL
            result: 请求结果
        """
        hash_key = self._generate_hash(workflow_name, prompt, width, height, urls)
        
        # 查找并更新记录
        for record in self.queue:
            if record.hash_key == hash_key:
                record.result = result
                record.timestamp = datetime.now()  # 更新时间戳
                break 
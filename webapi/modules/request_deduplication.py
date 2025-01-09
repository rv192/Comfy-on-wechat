from typing import Optional
from collections import deque
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import asyncio
from enum import Enum
from loguru import logger
from rich.console import Console

console = Console()

class RequestStatus(Enum):
    """请求状态"""
    PENDING = "pending"    # 正在处理
    COMPLETED = "completed"  # 处理完成
    FAILED = "failed"     # 处理失败

@dataclass
class RequestRecord:
    """请求记录"""
    hash_key: str
    timestamp: datetime
    status: RequestStatus
    result: Optional[dict]
    lock: asyncio.Lock  # 用于并发控制
    event: asyncio.Event  # 用于等待结果

class RequestDeduplication:
    """请求去重处理器"""
    def __init__(self, max_size: int = 100, time_window: int = 300):
        """
        初始化请求去重处理器
        
        Args:
            max_size: 队列最大长度，默认100条记录
            time_window: 时间窗口（秒），默认300秒（5分钟）
        """
        self.queue = deque(maxlen=max_size)
        self.time_window = time_window
        self._cleanup_lock = asyncio.Lock()
    
    def _generate_hash(self, workflow_name: str, prompt: str, width: int, height: int, urls: Optional[str]) -> str:
        """生成请求参数的哈希值"""
        params = {
            "workflow_name": workflow_name,
            "prompt": prompt,
            "width": width,
            "height": height,
            "urls": urls or ""
        }
        # 将参数转换为规范化的JSON字符串
        param_str = json.dumps(params, sort_keys=True)
        return hashlib.md5(param_str.encode()).hexdigest()
    
    async def _cleanup_expired(self):
        """清理过期的记录"""
        async with self._cleanup_lock:
            current_time = datetime.now()
            expired = []
            for record in self.queue:
                time_diff = (current_time - record.timestamp).total_seconds()
                # 只清理已完成或失败的过期记录，正在处理的记录不清理
                if time_diff > self.time_window and record.status != RequestStatus.PENDING:
                    expired.append(record)
            
            for record in expired:
                self.queue.remove(record)
    
    async def check_request(self, workflow_name: str, prompt: str, width: int, height: int, 
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
        # 清理过期记录
        await self._cleanup_expired()
        
        current_time = datetime.now()
        hash_key = self._generate_hash(workflow_name, prompt, width, height, urls)
        
        # 检查是否有重复请求
        for record in self.queue:
            if record.hash_key == hash_key:
                time_diff = (current_time - record.timestamp).total_seconds()
                if time_diff <= self.time_window:
                    console.print(f"\n[yellow]>>> ⚠️ 检测到重复请求[/yellow]")
                    console.print(f"[yellow]>>> 工作流: {workflow_name}[/yellow]")
                    console.print(f"[yellow]>>> 提示词: {prompt}[/yellow]")
                    console.print(f"[yellow]>>> 图片URL: {urls}[/yellow]")
                    console.print(f"[yellow]>>> 距离上次请求: {time_diff:.1f}秒[/yellow]")
                    
                    # 如果请求正在处理中，等待锁
                    async with record.lock:
                        if record.status == RequestStatus.COMPLETED and record.result is not None:
                            logger.info(f"发现重复请求，返回缓存结果: {hash_key}")
                            console.print(f"[green]>>> ✅ 返回缓存结果[/green]")
                            return record.result
                        elif record.status == RequestStatus.PENDING:
                            if time_diff > 240:  # 如果处理时间超过4分钟，认为可能出现问题
                                logger.warning(f"请求处理时间过长 ({time_diff:.1f}s)，允许重试: {hash_key}")
                                console.print(f"[red]>>> ⏰ 处理超时，允许重试[/red]")
                                record.status = RequestStatus.FAILED
                                return None
                            
                            logger.info(f"发现重复请求，等待处理结果 ({time_diff:.1f}s): {hash_key}")
                            console.print(f"[yellow]>>> ⌛️ 等待处理结果[/yellow]")
                            try:
                                # 等待结果，设置超时时间为180秒（3分钟）
                                await asyncio.wait_for(record.event.wait(), timeout=180.0)
                                if record.result is not None:
                                    console.print(f"[green]>>> ✅ 等待完成，返回结果[/green]")
                                    return record.result
                                else:
                                    # 如果等待后结果仍然为空，允许重试
                                    console.print(f"[red]>>> ❌ 等待完成但结果为空，允许重试[/red]")
                                    record.status = RequestStatus.FAILED
                                    return None
                            except asyncio.TimeoutError:
                                logger.warning(f"等待结果超时 ({time_diff:.1f}s)，允许重试: {hash_key}")
                                console.print(f"[red]>>> ⏰ 等待超时，允许重试[/red]")
                                record.status = RequestStatus.FAILED
                                return None
                            
                        elif record.status == RequestStatus.FAILED:
                            # 如果之前失败了，允许重试
                            console.print(f"[yellow]>>> 🔄 之前失败，允许重试[/yellow]")
                            record.status = RequestStatus.PENDING
                            record.timestamp = current_time
                            record.event.clear()  # 重置事件
                            return None
                
                # 如果记录已过期，更新状态
                record.status = RequestStatus.PENDING
                record.timestamp = current_time
                record.result = None
                record.event.clear()  # 重置事件
                return None
        
        # 如果没有找到记录，创建新记录
        new_record = RequestRecord(
            hash_key=hash_key,
            timestamp=current_time,
            status=RequestStatus.PENDING,
            result=None,
            lock=asyncio.Lock(),
            event=asyncio.Event()  # 添加事件对象
        )
        self.queue.append(new_record)
        
        return None
    
    async def update_result(self, workflow_name: str, prompt: str, width: int, height: int, 
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
                async with record.lock:
                    record.result = result
                    record.timestamp = datetime.now()
                    record.status = RequestStatus.COMPLETED if result.get("status") == "ok" else RequestStatus.FAILED
                    record.event.set()  # 设置事件，通知等待的请求
                break 
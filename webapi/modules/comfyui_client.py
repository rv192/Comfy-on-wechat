import random
import uuid
import json
import asyncio
import aiohttp
import websockets
from rich.console import Console
from loguru import logger
from modules.config import config
from tqdm import tqdm

console = Console()

class ComfyuiClient:
    def __init__(self, server: str = None):
        self.server_address = server or config.comfyui_srv
        self.client_id = str(uuid.uuid4())
        self.ws = None
        self._connected = False
        self.workflow_name = "未命名工作流"
        
    async def ensure_connected(self):
        """确保 WebSocket 连接是活跃的"""
        if not self._connected or not self.ws:
            try:
                self.ws = await websockets.connect(
                    f"ws://{self.server_address}/ws?clientId={self.client_id}",
                    ping_interval=20,
                    ping_timeout=20,
                    max_size=1024 * 1024 * 64,  # 设置为64MB
                    max_queue=None  # 不限制消息队列大小
                )
                self._connected = True
            except Exception as e:
                logger.error(f"WebSocket 连接失败: {e}")
                raise

    async def queue_prompt(self, prompt):
        """异步方式提交 prompt 到队列"""
        retries = 3
        while retries > 0:
            try:
                await self.ensure_connected()
                data = json.dumps({
                    "prompt": prompt,
                    "client_id": self.client_id
                }).encode('utf-8')
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"http://{self.server_address}/prompt",
                        data=data
                    ) as response:
                        return await response.json()
            except Exception as e:
                retries -= 1
                if retries == 0:
                    logger.error(f"提交 prompt 失败: {e}")
                    raise
                await asyncio.sleep(1)

    async def get_images(self, prompt, image_websocket_node, workflow_name: str = None):
        """异步方式获取生成的图片"""
        if workflow_name:
            self.workflow_name = workflow_name
            console.print(f"\n>>> 🚀 开始执行工作流: {self.workflow_name}")

        pbar = None
        try:
            await self.ensure_connected()
            prompt_id = (await self.queue_prompt(prompt))['prompt_id']
            output_images = {}
            current_node = ""

            async for message in self.ws:
                try:
                    if isinstance(message, str):
                        data = json.loads(message)
                        
                        if data['type'] == 'status':
                            queue_remaining = data['data']['status']['exec_info']['queue_remaining']
                            if queue_remaining > 1:
                                console.print(f">>> ⌛️ 进行中的任务数: {queue_remaining-1} ...")
                                
                        elif data['type'] == 'executing':
                            exec_data = data['data']
                            if exec_data['prompt_id'] == prompt_id:
                                if exec_data['node'] is None:
                                    break  # 执行完成
                                else:
                                    current_node = exec_data['node']
                                    console.print(f">> 节点[{current_node}]", end=" ")
                                    
                        elif data['type'] == 'progress':
                            pdata = data['data']
                            _v = pdata['value']
                            _max = pdata['max']
                            
                            if _v == 0:
                                continue
                            if _v == 1:
                                if pbar:
                                    pbar.close()
                                pbar = tqdm(
                                    total=_max,
                                    desc=f">> 节点[{pdata['node']}]",
                                    initial=1,
                                    colour=random.choice([
                                        "green", "blue", "red", "yellow",
                                        "magenta", "cyan", "white"
                                    ])
                                )
                            elif _v < _max:
                                if pbar:
                                    pbar.update()
                            else:
                                if pbar:
                                    pbar.update()
                                    pbar.close()
                                pbar = None
                    else:
                        # 处理二进制数据（图片）
                        if current_node == image_websocket_node:
                            console.print(">>> 接收图片...")
                            images_output = output_images.get(current_node, [])
                            images_output.append(message[8:])
                            output_images[current_node] = images_output
                            
                except Exception as e:
                    logger.error(f"处理消息时出错: {e}")
                    if pbar:
                        pbar.close()
                        pbar = None
                    continue

            return output_images
            
        except Exception as e:
            logger.error(f"获取图片时出错: {e}")
            raise
        finally:
            if pbar:
                pbar.close()

    async def close(self):
        """关闭连接并清理资源"""
        try:
            if self.ws:
                await self.ws.close()
        except Exception as e:
            logger.error(f"关闭 WebSocket 连接时出错: {e}")
        finally:
            self._connected = False
            self.ws = None

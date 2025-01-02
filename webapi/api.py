from contextlib import asynccontextmanager
from typing import Annotated, List
from fastapi import FastAPI, Header, Response, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import uvicorn
import os
import uuid
from datetime import datetime
from PIL import Image
from io import BytesIO
import psutil
import gc
from fastapi.responses import JSONResponse

from log_conf import init_logger_config
from modules import bizy_air
from req import *


# 配置图片保存目录
IMAGE_SAVE_DIR = "saved_images"
# 配置图片URL基础路径，请根据实际情况修改，例如 "http://your_host:8008/images/"
IMAGE_URL_BASE = "http://8.155.23.126:8008/images/"


# 确保图片保存目录存在
if not os.path.exists(IMAGE_SAVE_DIR):
    os.makedirs(IMAGE_SAVE_DIR)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """新版生命周期方法
    https://fastapi.tiangolo.com/advanced/events/
    """
    logger.info("startup_event")
    yield
    logger.info("shutdown_event")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 设置最大请求体积为 100MB
app.state.max_request_body_size = 100 * 1024 * 1024

@app.middleware("http")
async def check_request_body_size(request: Request, call_next):
    if request.method == "POST":
        content_length = request.headers.get('content-length')
        if content_length:
            content_length = int(content_length)
            if content_length > app.state.max_request_body_size:
                return JSONResponse(
                    status_code=413,
                    content={"detail": "请求体太大"}
                )
    response = await call_next(request)
    return response


@app.middleware("http")
async def monitor_memory(request: Request, call_next):
    # 获取当前内存使用情况
    memory = psutil.Process().memory_info()
    if memory.rss > 1024 * 1024 * 1024 * 2:  # 如果内存使用超过2GB
        gc.collect()  # 强制垃圾回收
        if memory.rss > 1024 * 1024 * 1024 * 2:
            return JSONResponse(
                status_code=503,
                content={"detail": "服务器资源不足，请稍后重试"}
            )
    
    response = await call_next(request)
    return response


@app.get("/")
async def root():
    return {"Hello": "comfyui-api", "version": "1.1.1"}


def save_image_and_get_url(image_bytes: bytes) -> str:
    """保存图片到服务器，并返回可访问的URL"""
    try:
        # 添加图片大小限制
        if len(image_bytes) > 50 * 1024 * 1024:  # 50MB
            raise HTTPException(status_code=413, detail="图片太大")
            
        image = Image.open(BytesIO(image_bytes))
        
        # 如果图片太大，可以考虑压缩
        max_size = (2000, 2000)  # 设置最大尺寸
        if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
            image.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # 创建以当前时间和随机UUID的唯一文件名
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d%H%M%S")
        unique_id = uuid.uuid4().hex
        filename = f"{timestamp}_{unique_id}.jpeg"
        file_path = os.path.join(IMAGE_SAVE_DIR, filename)
        
        image.save(file_path, "JPEG")

        # 生成可访问的图片URL
        image_url = f"{IMAGE_URL_BASE}{filename}"
        
        # 处理完后主动释放内存
        image.close()
        del image
        gc.collect()
        
        return image_url
    except Exception as e:
        logger.error(f"保存图片时出错: {e}")
        raise HTTPException(status_code=500, detail=f"保存图片失败: {e}")

@app.get("/images/{filename}")
async def get_image(filename: str):
    """处理获取图片请求"""
    file_path = os.path.join(IMAGE_SAVE_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="图片未找到")
    with open(file_path, "rb") as f:
        return Response(content=f.read(), media_type="image/jpeg")

@app.post("/comfy_gen", summary="通用 ComfyUI 生成")
async def comfy_gen(req: ComfyGenReq) -> dict:
    """通用 ComfyUI 生成接口"""
    try:
        imgs = bizy_air.comfyGen(req.workflow_name, req.prompt, req.img_content)
        if len(imgs) > 0:
            image_url = save_image_and_get_url(imgs[0])
            return {"image_url": image_url, "status": "ok"}
        return {"status": "error", "detail": "生成图片列表为空"}
    except Exception as e:
        logger.error(f"ComfyUI 生成出错: {e}")
        return {"status": "error", "detail": f"ComfyUI 生成失败: {e}"}


if __name__ == '__main__':
    log_level = "debug"
    init_logger_config(level=log_level)
    
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=8008,
        log_level=log_level,
        timeout_keep_alive=120,
    )
    server = uvicorn.Server(config)
    server.run()

from contextlib import asynccontextmanager
from typing import Annotated, List, Dict
from fastapi import FastAPI, Header, Response, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import uvicorn
import os
import uuid
from datetime import datetime
from PIL import Image
from io import BytesIO
import gc
import aiofiles
from fastapi.responses import JSONResponse

from log_conf import init_logger_config
from modules import bizy_air
from req import *
from modules.config import config
from modules.request_deduplication import RequestDeduplication

# 配置图片保存目录
IMAGE_SAVE_DIR = "saved_images"
# 构建图片URL基础路径
IMAGE_URL_BASE = config.image_url_base

# 初始化请求去重处理器
request_dedup = RequestDeduplication()

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

# 设置最大请求体积为 10MB
app.state.max_request_body_size = 10 * 1024 * 1024

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


@app.get("/")
async def root():
    return {"Hello": "comfyui-api", "version": "1.1.1"}


async def save_image_and_get_url(image_bytes: bytes) -> str:
    """异步方式保存图片到服务器，并返回可访问的URL"""
    try:
        # 添加图片大小限制
        if len(image_bytes) > 10 * 1024 * 1024:  # 10MB
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
        
        # 使用BytesIO进行内存中的操作
        img_byte_arr = BytesIO()
        image.save(img_byte_arr, format='JPEG')
        img_byte_arr = img_byte_arr.getvalue()

        # 异步写入文件
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(img_byte_arr)

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
    """异步处理获取图片请求"""
    file_path = os.path.join(IMAGE_SAVE_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="图片未找到")
    try:
        async with aiofiles.open(file_path, "rb") as f:
            content = await f.read()
            return Response(content=content, media_type="image/jpeg")
    except Exception as e:
        logger.error(f"读取图片时出错: {e}")
        raise HTTPException(status_code=500, detail=f"读取图片失败: {e}")

@app.post("/comfy_gen", summary="通用 ComfyUI 生成")
async def comfy_gen(req: ComfyGenReq) -> dict:
    """通用 ComfyUI 生成接口"""
    try:
        imgs = await bizy_air.comfyGen(req.workflow_name, req.prompt, req.img_content)
        if len(imgs) > 0:
            image_url = await save_image_and_get_url(imgs[0])
            return {"status": "ok", "image_url": image_url}
        return {"status": "error", "msg": "生成图片列表为空"}
    except Exception as e:
        logger.error(f"ComfyUI 生成出错: {e}")
        return {"status": "error", "msg": f"ComfyUI 生成失败: {e}"}

@app.post("/comfy_gen_v2", summary="通用 ComfyUI 生成 V2")
async def comfy_gen_v2(req: ComfyGenV2Req) -> dict:
    """通用 ComfyUI 生成接口 V2"""
    try:
        # 检查是否是重复请求
        cached_result = request_dedup.check_request(
            req.workflow_name,
            req.prompt,
            req.width,
            req.height,
            req.urls
        )
        
        if cached_result:
            logger.info(f"检测到重复请求，直接返回缓存结果")
            return cached_result
            
        imgs, image_usage_info = await bizy_air.comfyGenV2(
            req.workflow_name,
            req.prompt,
            req.width,
            req.height,
            req.urls
        )
        
        result = {}
        if len(imgs) > 0:
            image_url = await save_image_and_get_url(imgs[0])
            result = {
                "status": "ok",
                "image_url": image_url
            }
            # 如果有图片使用信息，添加到msg中
            if image_usage_info:
                result["msg"] = image_usage_info["msg"]
        else:
            result = {"status": "error", "msg": "生成图片列表为空"}
            
        # 更新请求记录的结果
        request_dedup.update_result(
            req.workflow_name,
            req.prompt,
            req.width,
            req.height,
            req.urls,
            result
        )
        
        return result
    except Exception as e:
        logger.error(f"ComfyUI 生成出错: {e}")
        return {"status": "error", "msg": f"ComfyUI 生成失败: {e}"}


if __name__ == '__main__':
    log_level = "debug"
    init_logger_config(level=log_level)
    
    uvicorn_config = uvicorn.Config(
        app,
        host="0.0.0.0",  # 监听所有网络接口
        port=config.webapi_port,
        log_level=log_level,
        timeout_keep_alive=120,
    )
    server = uvicorn.Server(uvicorn_config)
    server.run()

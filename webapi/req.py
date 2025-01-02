from typing import Optional
from pydantic import BaseModel, Field


class Txt2imgXhsReq(BaseModel):
    """小红书文生图请求体"""

    prompt: str = Field(description="文生图自然语言提示词")
    """文生图自然语言提示词"""
    clip_l: Optional[str] = Field(None, description="文生图标签提示词")
    """文生图标签提示词"""


class Img2imgXhsReq(BaseModel):
    """小红书图生图请求体"""

    img_content: str = Field(description="垫图base64字符串")
    """垫图base64字符串"""

class ComfyGenReq(BaseModel):
    """通用 ComfyUI 生成请求体"""
    workflow_name: str = Field(description="工作流名称")
    prompt: str = Field(description="生成提示词")
    img_content: str = Field(description="输入图片的base64字符串列表")

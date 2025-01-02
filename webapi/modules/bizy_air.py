import json
import os
import uuid
from typing import Optional

from loguru import logger

from modules import utils
from modules.comfyui_client import ComfyuiClient

def comfyGen(workflow_name: str, prompt: str = None, img_content: str = None):
    with open(f"./workflows/{workflow_name}.json", "r") as payload_json:
        payload = json.load(payload_json)
    
    prompt_node = "1"
    latent_node = "2"
    seed_node = "3"
    save_image_node = "99"

    # 处理提示词节点
    if prompt and prompt_node in payload:
        if "inputs" in payload[prompt_node]:
            if "t5xxl" in payload[prompt_node]["inputs"]:
                payload[prompt_node]["inputs"]["t5xxl"] = f"1girl, {prompt}"
            if "clip_l" in payload[prompt_node]["inputs"]:
                payload[prompt_node]["inputs"]["clip_l"] = f"1girl, {prompt}"

    if img_content:
        # 查找并处理所有图片输入节点
        image_nodes = []
        for node_id, node_data in payload.items():
            if node_data.get("class_type") == "NTL_LoadImagesBase64":
                image_nodes.append(node_id)

        if image_nodes: # 确保找到图片节点
            payload[image_nodes[0]]["inputs"]["images"] = f"[\"{img_content}\"]"
    
    # 处理尺寸，仅当节点存在时修改
    if latent_node in payload and "inputs" in payload[latent_node]:
        payload[latent_node]["inputs"]["width"] = 1024
        payload[latent_node]["inputs"]["height"] = 1024

    # 仅当种子节点存在时修改
    if seed_node in payload:
        payload[seed_node]["inputs"]["noise_seed"] = utils.get_seed()

    comfyui = ComfyuiClient()

    # 保存 JSON 到本地文件
    # tmp_dir = "tmpJson"
    # os.makedirs(tmp_dir, exist_ok=True)  # 确保目录存在
    # random_filename = f"{workflow_name}_{uuid.uuid4()}.json"
    # filepath = os.path.join(tmp_dir, random_filename)

    # with open(filepath, "w", encoding="utf-8") as file:
    #     json.dump(payload, file, ensure_ascii=False, indent=4)  # 使用 indent 4 方便阅读

    # logger.debug(f"保存 ComfyUI JSON 到: {filepath}")

    try:
        images_dict = comfyui.get_images(payload, save_image_node)
        return utils.receiving_image(images_dict)
    except Exception as e:
        logger.error(f"获取图片失败: {e}")
    finally:
        comfyui.close()
    return []

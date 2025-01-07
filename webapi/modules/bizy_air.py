import json
import os
import uuid
from typing import Optional
from rich.console import Console

from loguru import logger
from modules import utils
from modules.comfyui_client import ComfyuiClient

console = Console()

def comfyGen(workflow_name: str, prompt: str = None, img_content: str = None):
    """原始的 ComfyUI 生成函数"""
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
            if "text" in payload[prompt_node]["inputs"]:
                payload[prompt_node]["inputs"]["text"] = prompt

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

    try:
        images_dict = comfyui.get_images(payload, save_image_node, workflow_name)
        return utils.receiving_image(images_dict)
    except Exception as e:
        logger.error(f"获取图片失败: {e}")
    finally:
        comfyui.close()
    return []

def comfyGenV2(workflow_name: str, prompt: str = None, width: int = 1024, height: int = 1024, urls: str = None):
    """ComfyUI 生成函数 V2 版本"""
    
    # 添加 _v2 后缀，临时性操作，稳定后考虑删除
    if not workflow_name.endswith('_v2'):
        workflow_name = f"{workflow_name}_v2"
        
    workflow_path = os.path.join(os.path.dirname(__file__), '..', 'workflows', f"{workflow_name}.json")
    with open(workflow_path, "r") as payload_json:
        payload = json.load(payload_json)
    
    # 添加工作流名称到第一个节点的元数据中
    first_node = next(iter(payload))
    if first_node:
        if "_meta" not in payload[first_node]:
            payload[first_node]["_meta"] = {}
        payload[first_node]["_meta"]["workflow_name"] = workflow_name

    # 查找 SaveImageWebsocket 节点
    save_image_node = None
    for node_id, node_data in payload.items():
        if node_data.get("class_type") == "SaveImageWebsocket":
            save_image_node = node_id
            break
    
    if not save_image_node:
        console.print("[red]错误: 未找到 SaveImageWebsocket 节点[/red]")
        return []

    # 处理提示词节点
    if prompt:
        for node_id, node_data in payload.items():
            if (node_data.get("class_type") == "CR Text" and 
                node_data.get("_meta", {}).get("title", "").strip() == "🐉Prompt"):
                if "inputs" in node_data:
                    node_data["inputs"]["text"] = prompt

    # 处理宽度节点
    for node_id, node_data in payload.items():
        if (node_data.get("class_type") == "CR Integer Multiple" and 
            node_data.get("_meta", {}).get("title") == "🐉Width"):
            if "inputs" in node_data:
                node_data["inputs"]["integer"] = width

    # 处理高度节点
    for node_id, node_data in payload.items():
        if (node_data.get("class_type") == "CR Integer Multiple" and 
            node_data.get("_meta", {}).get("title") == "🐉Height"):
            if "inputs" in node_data:
                node_data["inputs"]["integer"] = height

    # 处理随机种子节点
    for node_id, node_data in payload.items():
        if (node_data.get("class_type") == "CR Integer Multiple" and 
            node_data.get("_meta", {}).get("title") == "🐉Seed"):
            if "inputs" in node_data:
                node_data["inputs"]["integer"] = utils.get_seed()

    # 处理图片输入
    image_usage_info = None
    if urls:
        # 查找所有 BizyAir_LoadImageURL 节点并按 title 排序
        image_nodes = []
        for node_id, node_data in payload.items():
            if node_data.get("class_type") == "BizyAir_LoadImageURL":
                title = node_data.get("_meta", {}).get("title", "")
                image_nodes.append((node_id, title))
        
        # 按 title 排序节点
        image_nodes.sort(key=lambda x: x[1])
        image_nodes = [node_id for node_id, _ in image_nodes]

        if image_nodes:
            # 将URL字符串分割成列表
            url_list = [url.strip() for url in urls.split("|") if url.strip()]
            
            if url_list:
                # 检查 URL 数量与节点数量的关系并记录日志
                if len(url_list) < len(image_nodes):
                    msg = f"提供的图片数量({len(url_list)})少于工作流所需数量({len(image_nodes)})，将循环使用已有图片"
                    console.print(f"[yellow]警告: {msg}[/yellow]")
                    image_usage_info = {"type": "cycle", "msg": msg}
                elif len(url_list) > len(image_nodes):
                    msg = f"提供的图片数量({len(url_list)})多于工作流所需数量({len(image_nodes)})，多余的图片将不会被使用"
                    console.print(f"[yellow]警告: {msg}[/yellow]")
                    image_usage_info = {"type": "truncate", "msg": msg}
                
                # 按排序后的顺序将URL分配给图片节点
                for idx, node_id in enumerate(image_nodes):
                    # 如果URL数量不够，则循环使用
                    url_idx = idx % len(url_list)
                    payload[node_id]["inputs"]["url"] = url_list[url_idx]

    comfyui = ComfyuiClient()

    try:
        images_dict = comfyui.get_images(payload, save_image_node, workflow_name)
        images = utils.receiving_image(images_dict)
        if image_usage_info:
            return images, image_usage_info
        return images, None
    except Exception as e:
        console.print(f"[red]错误: 获取图片失败: {e}[/red]")
    finally:
        comfyui.close()
    return [], None

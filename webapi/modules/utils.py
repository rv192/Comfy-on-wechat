import random
import base64
from modules.config import config

def get_seed():
    return random.randint(1, 1125899906842624)

def receiving_image(images_dict):
    """处理接收到的图片"""
    if not images_dict:
        return []
    
    image_urls = []
    for node_id, images in images_dict.items():
        for image_data in images:
            # 将 base64 图片数据转换为文件名
            image_name = base64.b64encode(image_data[:32]).decode('utf-8')[:32]
            image_name = image_name.replace('/', '_').replace('+', '-')
            image_url = f"{config.image_url_base}/view?filename={image_name}.png"
            image_urls.append(image_url)
    
    return image_urls

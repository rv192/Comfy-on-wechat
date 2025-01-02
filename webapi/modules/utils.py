import base64
import io
import random
from PIL import Image


MAX_SEED_VALUE = 4294967295
SAFE_MAX_SEED_VALUE = 2147483647
MIN_SEED_VALUE = 0


def get_seed() -> int:
    return random.randint(MIN_SEED_VALUE, MAX_SEED_VALUE)


def get_safe_seed() -> int:
    return random.randint(MIN_SEED_VALUE, SAFE_MAX_SEED_VALUE)


def receiving_image(images_dict: dict):
    imgs = []
    for node_id in images_dict:
        for inx, image_data in enumerate(images_dict[node_id]):
            image = Image.open(io.BytesIO(image_data)).convert('RGB')
            # 将图片转换为jpg格式
            buffer = io.BytesIO()
            image.save(buffer, format='JPEG')
            imgs.append(buffer.getvalue())
    return imgs

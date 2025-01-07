import base64
import io
import random
from PIL import Image

def get_seed():
    return random.randint(1, 1125899906842624)

def receiving_image(images_dict: dict):
    imgs = []
    for node_id in images_dict:
        for inx, image_data in enumerate(images_dict[node_id]):
            image = Image.open(io.BytesIO(image_data))
            buffer = io.BytesIO()
            if image.mode == "RGBA":
                white_image  = Image.new('RGB', image.size, (255, 255, 255))
                white_image.paste(image, mask=image.split()[3])
                white_image.save(buffer, format="JPEG")
            else:
                image.save(buffer, format="JPEG")
            imgs.append(buffer.getvalue())
    return imgs

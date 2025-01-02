import random
import uuid
from tqdm import tqdm
import websocket
import json
import urllib.request
import urllib.parse
from rich.console import Console


console = Console()


class ComfyuiClient(object):
    def __init__(self, server: str = "127.0.0.1:8188"):
        self.server_address = server
        self.client_id = str(uuid.uuid4())
        self.ws = websocket.WebSocket()
        self.ws.connect("ws://{}/ws?clientId={}".format(self.server_address, self.client_id))

    def queue_prompt(self, prompt):
        p = {"prompt": prompt, "client_id": self.client_id}
        data = json.dumps(p).encode('utf-8')
        req = urllib.request.Request(f"http://{self.server_address}/prompt", data=data, method='POST')
        return json.loads(urllib.request.urlopen(req).read())

    def get_images(self, prompt, image_websocket_node):
        prompt_id = self.queue_prompt(prompt)['prompt_id']
        output_images = {}
        current_node = ""
        while True:
            out = self.ws.recv()
            if isinstance(out, str):
                message = json.loads(out)
                if message['type'] == 'status':
                    queue_remaining = message['data']['status']['exec_info']['queue_remaining']
                    if queue_remaining > 1:
                        console.print(f">>> ⌛️ 进行中的任务数: {queue_remaining-1} ...")
                elif message['type'] == 'executing':
                    data = message['data']
                    if data['prompt_id'] == prompt_id:
                        if data['node'] is None:
                            break  # Execution is done
                        else:
                            current_node = data['node']
                            console.print(f">> 节点[{current_node}]", end=" ")
                elif message['type'] == 'progress':
                    pdata = message['data']
                    _v = pdata['value']
                    _max = pdata['max']
                    if _v == 0:
                        continue
                    if _v == 1:
                        pbar = tqdm(total=_max, desc=f">> 节点[{pdata['node']}]", initial=1,
                                    colour=random.choice(["green", "blue", "red", "yellow", "magenta", "cyan", "white"]))
                    elif _v < _max:
                        if pbar:
                            pbar.update()
                    else:
                        if pbar:
                            pbar.update()
                            pbar.close()
            else:
                if current_node == image_websocket_node:
                    console.print(">>> 接收图片...")
                    images_output = output_images.get(current_node, [])
                    images_output.append(out[8:])
                    output_images[current_node] = images_output

        return output_images

    def close(self):
        self.ws.close()

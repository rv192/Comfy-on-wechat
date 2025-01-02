# comfyui-api

以API的形式提供comfyui的接口，方便其他项目调用。

## 安装依赖

```bash
# python版本不小于3.10，建议使用3.12
pip install -r requirements.txt
```

## 修改comfyui的地址

在`modules/comfyui_client.py`中修改comfyui的地址，默认是`127.0.0.1:8188`，如果需要修改，请修改为comfyui的地址。

## 启动

```bash
python api.py
```

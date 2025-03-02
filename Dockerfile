FROM richard1573/comfyui:latest

# 切换到 root 用户
USER root

# 安装 nano
RUN apt-get update && apt-get install -y nano tini

# 设置工作目录
WORKDIR /app/ComfyUI
RUN git config --global --add safe.directory /app/ComfyUI

# 恢复默认用户（确保检查基础镜像的用户UID并替换下面的1000）
USER 1000

# 更新 ComfyUI
RUN git pull

# 安装 BizyAir
WORKDIR /app/ComfyUI/custom_nodes
RUN git clone https://github.com/siliconflow/BizyAir.git
RUN if [ -f "/app/ComfyUI/custom_nodes/BizyAir/requirements.txt" ]; then pip install -r /app/ComfyUI/custom_nodes/BizyAir/requirements.txt; fi

# 安装 Comfyroll_CustomNodes
RUN git clone https://github.com/Suzie1/ComfyUI_Comfyroll_CustomNodes.git
RUN if [ -f "/app/ComfyUI/custom_nodes/ComfyUI_Comfyroll_CustomNodes/requirements.txt" ]; then pip install -r /app/ComfyUI/custom_nodes/ComfyUI_Comfyroll_CustomNodes/requirements.txt; fi

# 安装ComfyUI-AutoCropFaces等关键节点
RUN git clone https://github.com/liusida/ComfyUI-AutoCropFaces.git
RUN if [ -f "/app/ComfyUI/custom_nodes/ComfyUI-AutoCropFaces/requirements.txt" ]; then pip install -r /app/ComfyUI/custom_nodes/ComfyUI-AutoCropFaces/requirements.txt; fi

RUN git clone https://github.com/cubiq/ComfyUI_essentials.git
RUN if [ -f "/app/ComfyUI/custom_nodes/ComfyUI_essentials/requirements.txt" ]; then pip install -r /app/ComfyUI/custom_nodes/ComfyUI_essentials/requirements.txt; fi

# 更新 ComfyUI-Manager
WORKDIR /app/ComfyUI/custom_nodes/ComfyUI-Manager
RUN git pull

# 返回上一级目录
WORKDIR /app/ComfyUI

# 克隆 Comfy-on-wechat
RUN git clone https://github.com/rv192/Comfy-on-wechat.git

# 移动 webapi 目录
RUN mv Comfy-on-wechat/webapi .

RUN pip install spandrel

# 安装 webapi requirements
WORKDIR /app/ComfyUI/webapi
RUN pip3 install -r requirements.txt

# 返回上一级目录
WORKDIR /app/ComfyUI

# 暴露端口
EXPOSE 8188
EXPOSE 8008

# 将容器的启动命令设置为 tini (假设基础镜像使用了tini)
ENTRYPOINT ["/usr/bin/tini", "--"]

USER root

# 使用 CMD 启动一个 shell 脚本
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh
CMD ["/app/start.sh"]


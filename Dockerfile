FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# 1. 安装系统依赖
RUN apt-get update && \
    apt-get install -y \
    python3.10 \
    python3-pip \
    python3.10-venv \
    build-essential \
    libopus-dev \
    libopus0 \
    ffmpeg \
    git \
    git-lfs \
    && \
    rm -rf /var/lib/apt/lists/*

# 2. 创建一个 *空的* venv
# (将在 compose 中将依赖安装到它的 site-packages)
RUN python3.10 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 3. 升级 pip 本身
RUN pip install --upgrade pip

# 4. 设置工作目录并复制 *所有* 代码和模型
WORKDIR /app
COPY . .

# 5. 确保 entrypoint.sh 可执行
RUN chmod +x /app/entrypoint.sh

# 6. 声明配置卷
VOLUME /config

# 7. 暴露主服务端口和配置 UI 端口
EXPOSE 8000
EXPOSE 8080

# 8. 设置启动脚本作为 entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
## 操作说明

提供本地部署和容器部署两种方式。（开发阶段，尚不稳定，谨慎观望）

### 一、本地部署

1. 拉取仓库（递归更新子模块）

   ```bash
   git clone --recursive https://github.com/haoruanwn/AIChat_server.git
   ```

2. 创建虚拟环境（以conda为例）

   ```
   cd ./AIChat_server
   conda create --prefix ./AIChatServerEnv python=3.10
   ```

3. 激活虚拟环境并安装python依赖

   ```
   conda activate ./AIChatServerEnv
   pip install -r ./requirements.txt
   ```

4. 运行（可能要赋予脚本可执行权限）

   ```
   ./entrypoint.sh
   ```

### 二、容器部署

以docker为例

在工作文件夹创建`docker-compose.yml`文件，填入以下内容

```yaml
version: '3.8'

services:
  aichat-server:
    # 从GHCR拉取最新的镜像
    image: ghcr.io/haoruanwn/aichat_server:latest
    
    # 映射配置 UI 端口（主服务由网页管理生命周期）
    ports:
      - "8080:8080"    # 配置 UI 和服务管理端口
      - "8000:8000"    # WebSocket 服务端口
    
    restart: unless-stopped

    # 挂载卷
    volumes:
      # 配置文件持久化
      - aichat_config:/config
      
      # 依赖缓存
      - aichat-deps-vol:/app/deps
      
      # modelscope 缓存
      - aichat-cache-vol:/root/.cache/modelscope
      
      # 日志
      - aichat-logs-vol:/app/logs

    # 环境变量
    environment:
      - PYTHONPATH=/app/deps
      - CONFIG_PATH=/config/config.json

# 定义持久化卷
volumes:
  aichat_config:
    driver: local
  aichat-deps-vol:
  aichat-cache-vol:
  aichat-logs-vol:

```

运行docker compose

```bash
docker-compose up -d 

#如果docker版本比较新
docker compose up -a
```


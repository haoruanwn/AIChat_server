## AI语言助手demo(Server端)

### 环境搭建

这里默认大家都是用的自己的电脑搭建服务，默认同学们都没有GPU（有就更好）

首先创建虚拟环境, 不然容易污染你的系统环境, 作者使用的python3.10。环境名字就起名`AIChatServerEnv`好了，环境名可自定义。

``` sh
cd ./your-path
conda create --prefix ./AIChatServerEnv python=3.10
```


然后启动虚拟环境，并安装所需要的包，如果下载不了需要科学上网

``` sh
conda activate ./AIChatServerEnv
pip install -r ./requirments.txt
```

搭建完毕，直接运行即可了, access_token是Client端匹配的密码，aliyun_api_key是阿里云的API key，用于访问通义千问

``` sh
python ./main.py --access_token="123456" --aliyun_api_key="sk-your-api-key"
```

### 文件目录介绍

```sh
Server/
├── config/                # 全局设置
├── handle/                # ws接收内容的处理
|   ├── audio_handle.py    # 音频数据处理
|   ├── auth_handle.py     # 鉴权
│   └── text_handle.py     # 文本数据处理
├── models/                # 
├── services/              # 
├── test/                  # 单功能测试
├── threads/               # 多线程相关
├── tools/                 # 工具
|   ├── audio_processor.py # 音频处理
|   ├── logger.py          # log
│   └── registry.py        # 意图注册
├── ws_server.py           # websocket server 业务
├── service_manager.py     # services 全局管理
└── main.py
```

### WebSockets协议说明

以下是Server端会向Client端发送的信息:

1. 鉴权信息：

   ```json
   {
      "type": "auth",
      "message": "Authentication failed" 
   }
   ```
   "message"还包括: "Client authenticated"

2. VAD检测到说话的活跃状态

   ```json
   {
      "type": "vad",
      "state": "no_speech" 
   }
   ```
   "state"还包括: "end", "too_long"

3. ASR识别到说话的文字

   ```json
   {
       "type": "asr",
       "text": "speech的内容"
   }
   ```

4. tts生成语音完毕

   ```json
   {
      "type": "tts",
      "state": "end"
   }
   ```
   "state"还包括: "continue"

5. 对话结束

   ```json
   {
      "type": "chat",
      "dialogue": "end"
   }
   ```
   "state"还包括: "continue"


6. 打包发送的音频数据

   ```python
    version: 协议版本 (2 字节)
    type: 消息类型 (2 字节)
    payload: opus格式消息负载 (字节)
   ```

部署用docker-compose.yml
```yaml
version: '3.8'

services:
  aichat-server:
    build:
      context: .
      dockerfile: Dockerfile
    image: aichat-server:local-test
    platform: linux/amd64
    
    # 修正: 端口从 8765 -> 8000
    ports:
      - "8000:8000"
    
    restart: unless-stopped

    # 修正: 环境变量现在由 .env 文件自动提供
    # 我们不再需要 'environment:' 块
    
    volumes:
      - ./model_cache:/root/.cache/modelscope

    # 修正: 环境变量会从 .env 自动注入
    # command 保持不变
    command: >
      python ./main.py
        --access_token="${ACCESS_TOKEN}"
        --aliyun_api_key="${ALIYUN_API_KEY}"
```

```yaml
services:
  aichat-server:
    # 1. 拉取你刚刚在 GHCR 上发布的镜像
    # (!! 记得替换为你自己的用户名/仓库名 !!)
    image: ghcr.io/haoruanwn/aichat_server:latest
    
    platform: linux/amd64
    ports:
      - "8000:8000"
    restart: unless-stopped

    # 2. (关键) 挂载
    volumes:
      # 2.1: (你的需求) 将本地的 'python_deps' 目录
      #      挂载到容器 venv 的 'site-packages' 目录
      - ./python_deps:/opt/venv/lib/python3.10/site-packages
      
      # 2.2: (不变) 挂载模型缓存 (用于 modelscope 动态下载)
      - ./model_cache:/root/.cache/modelscope
      
      # 2.3: (不变) 挂载日志
      - ./logs:/app/logs

    # 3. (关键) 启动命令:
    #    a) 激活 venv
    #    b) 运行 pip install (它会安装到 ./python_deps)
    #    c) 运行 python 程序
    command: >
      bash -c "
        echo '🚀 [Nexus] 正在激活 venv 并安装/检查 Python 依赖...'
        source /opt/venv/bin/activate && \
        pip install -r requirements.txt && \
        echo '✅ [Nexus] 依赖安装完成。正在启动服务...' && \
        python ./main.py \
          --access_token='${ACCESS_TOKEN}' \
          --aliyun_api_key='${ALIYUN_API_KEY}'
      "
    
    # 4. (关键) .env 文件
    #    告诉 compose 在此目录查找 .env 文件
    env_file: .env

# 5. (可选) 显式定义卷，以便 Docker 知道它们是持久化的
volumes:
  python_deps:
  model_cache: 
  logs:
```
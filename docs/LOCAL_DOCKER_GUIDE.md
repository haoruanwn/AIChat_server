# 🚀 本地 Docker 运行指南

## ✅ 当前状态


```
✔ Container server-aichat-server-1  Running
✔ Network server_default            Created
✔ Configuration UI Server           Started on port 8080
```

---

## 🌐 如何访问 Web UI

### 在本地计算机上：

打开浏览器，访问：
```
http://localhost:8080
```

或者：
```
http://127.0.0.1:8080
```

### 网页应该会显示：

一个专业的配置管理界面，包括：

1. **🔌 服务状态面板**
   - 显示服务是否运行（✅ 运行中 / ⏹️ 已停止）
   - 显示进程 ID (PID)
   - 三个按钮：启动 / 停止 / 重启

2. **🔑 API 配置**
   - 访问令牌 (ACCESS_TOKEN)
   - 阿里云 API Key (ALIYUN_API_KEY)

3. **🤖 AI 配置**
   - 机器人名称（默认：Echo）
   - 聊天模型选择
   - 意图识别模型选择
   - API 超时时间
   - 系统提示词（可自定义）

4. **💻 硬件配置**
   - ASR 设备选择（CPU/GPU）
   - VAD 设备选择（CPU/GPU）

5. **💾 操作按钮**
   - 保存配置
   - 重置表单

---

## 📝 使用步骤

### 第 1 步：填写配置

1. 打开 http://localhost:8080
2. 填写必要信息：
   - **ACCESS_TOKEN**: 例如 `123456`
   - **ALIYUN_API_KEY**: 从 https://bailian.console.aliyun.com/ 获取（必填）
3. 修改 AI 配置（可选）：
   - 机器人名称
   - 系统提示词
   - 模型选择

### 第 2 步：保存配置

点击页面底部的 **"💾 保存配置"** 按钮

你会看到成功提示：
```
✅ 配置已保存
```

### 第 3 步：启动服务

1. 返回页面顶部，查看 **"🔌 服务状态"** 面板
2. 点击 **"▶️ 启动服务"** 按钮
3. 等待 1-2 秒，服务会自动启动
4. 状态会更新为：**"✅ 运行中"**

### 第 4 步：服务已就绪

现在你的 WebSocket 服务运行在：
```
ws://localhost:8000
```

客户端可以连接到这个地址进行通信。

---

## 🛠️ 常用操作

### 查看容器状态

```bash
docker compose ps
```

输出应该显示：
```
NAME                     IMAGE                  PORTS
server-aichat-server-1   aichat-server:latest   0.0.0.0:8000->8000/tcp, 0.0.0.0:8080->8080/tcp
```

### 查看日志

```bash
# 查看所有日志
docker compose logs aichat-server

# 实时跟踪日志
docker compose logs -f aichat-server

# 查看最后 50 行
docker compose logs --tail=50 aichat-server
```

### 重启服务

有三种方式：

**方式 1：通过 Web UI**（推荐）
- 点击 "🔄 重启服务" 按钮

**方式 2：停止后重启**
```bash
docker compose down
docker compose up -d
```

**方式 3：重建镜像**
```bash
docker compose build --no-cache
docker compose up -d
```

### 停止容器

```bash
docker compose down
```

### 进入容器

```bash
docker exec -it server-aichat-server-1 bash
```

在容器内，你可以：
- 查看文件：`ls -la /app`
- 查看配置：`cat /config/config.json`
- 查看日志：`tail -f /app/logs/assistant_*.log`

---

## 📂 重要路径

| 路径 | 说明 |
|------|------|
| `/config/config.json` | 配置文件（Docker 卷挂载，持久化） |
| `/app/main.py` | 主服务入口 |
| `/app/config_ui.py` | Web UI 服务 |
| `/app/logs/` | 日志文件目录 |
| `/app/web_ui/` | Web UI 前端文件 |

### 访问配置文件

配置文件保存在 Docker 卷中，可以通过以下方式查看：

```bash
# 查看配置内容
docker exec server-aichat-server-1 cat /config/config.json
```

或者在容器内：
```bash
docker exec -it server-aichat-server-1 bash
cat /config/config.json
```

---

## 🔄 服务生命周期

```
启动 Docker 容器
    ↓
运行 entrypoint.sh
    ↓
启动 config_ui.py (Web UI 服务 :8080)
    ↓
用户打开浏览器 http://localhost:8080
    ↓
填写配置 → 保存到 /config/config.json
    ↓
点击 "▶️ 启动服务" 按钮
    ↓
config_ui.py 启动 main.py (WebSocket 服务 :8000)
    ↓
Python 服务正常运行
    ↓
客户端连接 ws://localhost:8000
```

---

## 🐛 故障排除

### 问题 1：无法访问 http://localhost:8080

**检查步骤：**
```bash
# 1. 检查容器是否运行
docker compose ps

# 2. 查看日志
docker compose logs aichat-server

# 3. 检查端口是否被占用
lsof -i :8080

# 如果被占用，使用其他端口
docker compose down
# 编辑 docker-compose.yml，修改 8080:8080 为其他端口，如 9080:8080
docker compose up -d
```

### 问题 2：配置保存失败

**检查步骤：**
```bash
# 1. 检查配置目录是否存在
docker exec server-aichat-server-1 ls -la /config/

# 2. 检查目录权限
docker exec server-aichat-server-1 ls -ld /config

# 3. 查看完整日志
docker compose logs aichat-server
```

### 问题 3：启动服务时失败

**检查步骤：**
```bash
# 1. 检查配置是否完整
docker exec server-aichat-server-1 cat /config/config.json | python -m json.tool

# 2. 检查 API Key 是否有效
docker compose logs aichat-server | grep -i "api\|key"

# 3. 手动启动服务查看具体错误
docker exec -it server-aichat-server-1 python main.py
```

### 问题 4：容器一直重启

**原因：** entrypoint.sh 返回错误

**解决方案：**
```bash
# 查看完整日志（包括错误）
docker compose logs --tail=100 aichat-server

# 进入容器调试
docker run -it --entrypoint bash aichat-server:latest

# 或者修改 docker-compose.yml，添加 override command
docker compose run --rm aichat-server /bin/bash
```

---

## 📊 监控服务

### 实时查看资源使用

```bash
docker stats server-aichat-server-1
```

输出示例：
```
CONTAINER           CPU %     MEM USAGE / LIMIT
server-aichat-s...  0.5%      450MiB / 7.8GiB
```

### 检查端口开放

```bash
# 检查 8080 和 8000 端口
netstat -ln | grep -E "8080|8000"

# 或者使用 lsof
lsof -i :8080
lsof -i :8000
```

---

## ✅ 验收清单

启动完成后，检查以下项目：

- [ ] 容器正在运行：`docker compose ps`
- [ ] Web UI 可访问：`http://localhost:8080` 能打开
- [ ] 能看到服务状态面板
- [ ] 能填写和保存配置
- [ ] 能通过 Web UI 启动服务
- [ ] 服务启动后状态更新为"✅ 运行中"
- [ ] WebSocket 服务在 `ws://localhost:8000` 可用

---

## 🎉 下一步

1. **配置 AI 人设**
   - 修改"机器人名称"（默认 Echo）
   - 修改"系统提示词"自定义 AI 行为

2. **获取 API Key**
   - 访问 https://bailian.console.aliyun.com/
   - 创建 API Key
   - 填入 Web UI

3. **启动服务**
   - 保存配置
   - 点击"启动服务"

4. **连接客户端**
   - 使用 WebSocket 客户端连接 `ws://localhost:8000`
   - 开始交互

---

**祝你使用愉快！如有问题，查看日志会很有帮助。** 🚀

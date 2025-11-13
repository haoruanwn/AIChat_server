# 🚀 5 分钟快速开始

## 📋 你现在的状态

✅ Docker 容器已启动
✅ Web UI 服务正在运行
✅ 系统已准备好配置

---

## 🌐 打开 Web 界面

### 在你的浏览器中打开：

```
http://localhost:8080
```

**如果在远程服务器，替换为：**
```
http://<你的服务器IP>:8080
```

---

## 📝 配置步骤（只需 3 步！）

### ✏️ 步骤 1：填写表单

Web 界面打开后，你会看到配置表单。需要填写：

| 字段 | 说明 | 示例 |
|------|------|------|
| **访问令牌** | 客户端连接时的密码 | `123456` |
| **阿里云 API Key** ⭐ | **必填**，从阿里云获取 | `sk-abc123...` |
| **机器人名称** | AI 助手的名字 | `Echo` |
| **系统提示词** | AI 的角色描述 | `你是一个友好的助手...` |

其他字段可以保持默认。

### 💾 步骤 2：保存配置

点击页面底部的 **"💾 保存配置"** 按钮

页面会显示：
```
✅ 配置已保存
```

### ▶️ 步骤 3：启动服务

1. 滚动到页面顶部
2. 在 **"🔌 服务状态"** 部分，点击 **"▶️ 启动服务"** 按钮
3. 等待 1-2 秒
4. 状态会更新为 **"✅ 运行中"**

---

## ✅ 服务已准备好！

现在你的 WebSocket 服务运行在：

```
ws://localhost:8000
```

客户端可以连接使用了！

---

## 🎮 Web UI 功能速览

### 上面部分 - 服务控制

```
🔌 服务状态 [✅ 运行中]
┌─────────────────────────────────────┐
│ ▶️ 启动服务  🔄 重启服务  ⏹️ 停止服务 │
│ PID: 12345                          │
└─────────────────────────────────────┘
```

### 下面部分 - 配置表单

**🔑 API 配置**
- ACCESS_TOKEN
- ALIYUN_API_KEY

**🤖 AI 配置**
- 机器人名称
- 聊天模型选择
- 系统提示词
- 硬件设备选择

**💾 操作**
- 保存配置
- 重置表单

---

## 🚨 常见问题

### Q：访问不了 http://localhost:8080？

A：尝试：
```bash
# 检查容器是否运行
docker compose ps

# 检查端口是否监听
netstat -ln | grep 8080

# 查看日志
docker compose logs aichat-server
```

### Q：API Key 怎么获取？

A：
1. 访问 https://bailian.console.aliyun.com/
2. 登录你的阿里云账户
3. 创建或查看 API Key
4. 复制 Key 并粘贴到表单

### Q：修改配置后需要重启吗？

A：是的，点击 **"🔄 重启服务"** 按钮即可应用新配置。

### Q：可以停止服务吗？

A：可以，点击 **"⏹️ 停止服务"** 按钮。Web UI 仍然可用，可继续修改配置。

### Q：配置会保存吗？

A：会的！配置保存在 Docker 卷中，容器重启后配置依然存在。

---

## 📊 实时监控

### 在另一个终端查看日志

```bash
docker compose logs -f aichat-server
```

你会看到实时的服务运行日志。

### 查看资源使用

```bash
docker stats server-aichat-server-1
```

---

## 🔧 如果遇到问题

### 完全重启

```bash
docker compose down
docker compose up -d
```

### 查看详细日志

```bash
docker compose logs --tail=100 aichat-server
```

### 进入容器调试

```bash
docker exec -it server-aichat-server-1 bash
```

在容器内可以：
```bash
# 查看配置
cat /config/config.json

# 查看日志
tail -f /app/logs/assistant_*.log

# 测试 API
curl http://localhost:8080/api/health
```

---

## 🎯 下一步

1. ✅ Web UI 填写配置
2. ✅ 获取并输入 API Key
3. ✅ 启动服务
4. 🔜 使用 WebSocket 客户端连接 `ws://localhost:8000`

---

**准备好了吗？打开浏览器，访问 http://localhost:8080 开始吧！** 🚀

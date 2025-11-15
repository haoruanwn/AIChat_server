# 快速启动指南 - AIChat 实时日志系统

## 📋 前置要求

- Python 3.10+
- 已安装所有依赖（`pip install -r requirements.txt`）
- 虚拟环境已激活

## 🚀 启动步骤

### 1. 启动配置UI和WebSocket服务
```bash
cd /path/to/AIChat_server
conda activate ./AIChatServerEnv  # 或你的虚拟环境

./entrypoint.sh
```

这会同时启动：
- `config_ui.py` 在 `http://localhost:8080`
- WebSocket服务在 `ws://localhost:8000`

### 2. 访问Web配置界面
打开浏览器访问：
```
http://localhost:8080
```

### 3. 查看实时日志

#### 方法 A：从配置页面导航
1. 访问 `http://localhost:8080/config.html`
2. 在左侧边栏找到 **"📜 服务日志"** 菜单项
3. 点击进入日志查看页面

#### 方法 B：直接访问
```
http://localhost:8080/logs.html
```

## 🎯 使用日志页面

### 页面元素说明

```
┌─────────────────────────────────────────────────┐
│  AIChat 实时服务日志          [已连接] (绿色)   │  ← 连接状态
├─────────────────────────────────────────────────┤
│                                                  │
│  WebSocket server started on ws://0.0.0.0:8000 │
│  Waiting for connections...                     │
│  [2024-11-15 10:30:45] AI service initialized   │
│                                                  │  ← 日志区域
│                                                  │     (自动滚动)
│                                                  │
│                                                  │
├─────────────────────────────────────────────────┤
│ [返回配置页] [清空日志] [✓ 自动滚动]            │
└─────────────────────────────────────────────────┘
```

### 连接状态指示器

| 状态 | 颜色 | 含义 |
|------|------|------|
| 连接中... | 🟠 黄色 | 正在建立WebSocket连接 |
| 已连接 | 🟢 绿色 | 已成功连接，实时接收日志 |
| 已断开 | 🔴 红色 | 连接断开，自动重连中 |
| 连接失败 | 🔴 红色 | 连接异常 |

## 🔄 常见操作

### 启动主服务并查看日志

1. **打开日志页面** (保持开启)
   ```
   http://localhost:8080/logs.html
   ```
   页面显示 "已连接" (绿色)

2. **打开另一个标签页到配置页**
   ```
   http://localhost:8080/config.html
   ```

3. **点击 "▶️ 启动服务" 按钮**

4. **切换回日志页面** 
   应看到类似日志：
   ```
   Starting AIChat main service...
   [INFO] WebSocket server started on ws://0.0.0.0:8000
   [INFO] Waiting for connections...
   Log reader thread started...
   Service started successfully (PID: 12345)
   ```

### 停止服务并查看日志

1. **在配置页点击 "⏹️ 停止服务" 按钮**

2. **日志页面显示**
   ```
   Stopping AIChat service...
   Service stopped successfully
   Log reader thread stopped (process stdout closed).
   ```

### 查看AI对话日志

1. **保持日志页面开启**

2. **在配置页启动服务**

3. **用外部客户端连接到WebSocket**
   ```bash
   # 示例：使用 wscat 工具
   wscat -c ws://localhost:8000
   ```

4. **发送请求** → 日志页面实时显示处理过程
   ```
   [INFO] audio_handler: Received audio chunk
   [INFO] service_manager: Processing audio...
   [INFO] llm_model: Generating response...
   [INFO] tts_service: Synthesizing speech...
   ```

### 清空日志内容

点击 **"清空日志"** 按钮清除当前显示的所有日志。

> ⚠️ 注意：这只清空了页面显示，服务日志本身不受影响。

### 禁用自动滚动

取消勾选 **"自动滚动"** 复选框，当手动向上浏览历史日志时很有用。

## ⚙️ 配置与定制

### 环境变量

```bash
# 强制Python使用非缓冲输出（自动设置）
export PYTHONUNBUFFERED=1

# 配置文件路径（可选）
export CONFIG_PATH=/path/to/config.json

# WebSocket日志端点（已硬编码）
WS_LOGS_ENDPOINT=/ws/logs
```

### 修改日志显示样式

编辑 `web_ui/logs.html` 中的 `<style>` 部分：

```html
<style>
    /* 修改背景颜色 */
    body { background: #0f172a; /* 改为你想要的颜色 */ }
    
    /* 修改字体大小 */
    #log-output { font-size: 13px; /* 改为你想要的大小 */ }
    
    /* 修改字体 */
    body { font-family: '你的字体', monospace; }
</style>
```

### 日志刷新频率

日志是**实时推送**的，没有刷新延迟。WebSocket确保最小延迟。

## 🐛 故障排查

### 问题 1：日志页面显示 "连接失败"

**可能原因：**
- `config_ui.py` 未正常运行
- 防火墙阻止WebSocket连接
- 浏览器开发者工具中显示CORS错误

**解决方案：**
```bash
# 检查config_ui是否运行
ps aux | grep config_ui

# 检查8080端口是否开放
netstat -tuln | grep 8080

# 查看浏览器控制台错误 (F12 → Console)
```

### 问题 2：日志显示 "已断开" (红色)

**可能原因：**
- WebSocket连接超时
- 网络不稳定
- 服务端崩溃

**解决方案：**
- 页面会自动重连（等待10秒内）
- 检查 `config_ui.py` 是否还在运行
- 重启 `config_ui.py` 服务

### 问题 3：看不到 main.py 的日志

**可能原因：**
- `main.py` 还未启动（从配置页启动）
- 日志被缓冲（应已设置PYTHONUNBUFFERED=1）
- 日志出现在stderr而非stdout

**解决方案：**
```python
# 检查 main.py 的日志设置
# 确保使用 logger.info() 而非 print()
# 检查 tools/logger.py 的StreamHandler配置
```

### 问题 4：日志自动滚动不工作

**解决方案：**
1. 确保勾选了 "自动滚动" 复选框
2. 刷新页面 (Ctrl+R / Cmd+R)
3. 检查浏览器开发者工具是否有JavaScript错误

### 问题 5：日志滚动很卡/延迟大

**可能原因：**
- 日志输出过于频繁
- 浏览器性能问题
- 网络延迟

**解决方案：**
```javascript
// 可以在logs.js中调整 scrollTop 频率
// 或减少日志输出量
```

## 📊 监控指标

### 浏览器开发者工具 (F12)

**Network 标签：**
- 查看WebSocket连接状态
- 检查消息大小和频率

**Console 标签：**
```javascript
// 查看连接状态日志
// 示例输出：
// Log WebSocket connected.
// Reconnecting...
```

**Performance 标签：**
- 监控浏览器DOM更新性能
- 检查内存泄漏

### 服务端监控

在 `config_ui.py` 的终端中查看：
```
Log client connected. Total clients: 1
Log broadcaster task started.
[线程继续输出 main.py 的所有日志]
Log client removed. Total clients: 0
```

## 🔐 安全建议

### 生产环境部署

1. **使用HTTPS和WSS**
   ```python
   # 配置SSL证书
   uvicorn.run(app, 
               host="0.0.0.0", 
               port=8080,
               ssl_keyfile="/path/to/key.pem",
               ssl_certfile="/path/to/cert.pem")
   ```

2. **添加身份验证**
   ```python
   # 在 /ws/logs 端点添加token验证
   @app.websocket("/ws/logs")
   async def websocket_log_endpoint(websocket: WebSocket, token: str = Query(...)):
       if not verify_token(token):
           await websocket.close(code=1008)
   ```

3. **限制日志敏感信息**
   ```python
   # 在 log_reader_thread 中过滤敏感信息
   if "password" in line.lower() or "api_key" in line.lower():
       line = "[REDACTED]"
   ```

## 📚 更多资源

- [FastAPI WebSocket文档](https://fastapi.tiangolo.com/advanced/websockets/)
- [Python asyncio文档](https://docs.python.org/3/library/asyncio.html)
- [WebSocket API文档](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)

---

**需要帮助？** 查看 `IMPLEMENTATION_SUMMARY.md` 了解详细实现细节。

祝您使用愉快！ 🎉

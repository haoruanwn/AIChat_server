# AIChat Server 实时日志流式传输实现总结

## 概述

已成功实现了一个**生产级的日志流式传输系统**，将后端进程（`main.py`）的标准输出实时、非阻塞地流式传输到Web前端，并通过WebSocket进行广播。

## 解决的问题

### 原有问题
- `config_ui.py` 中使用了 `subprocess.Popen` 启动 `main.py`，但指定了 `stdout=subprocess.PIPE` 却**从未读取**管道
- 当 `main.py` 的日志缓冲区写满后，会**阻塞I/O并冻结**整个服务
- 无法实时查看子进程的日志

### 新解决方案
✅ 使用**专用线程**非阻塞地读取子进程日志  
✅ 通过**线程安全队列**连接同步线程和异步FastAPI  
✅ 实现**WebSocket广播**将日志推送到所有连接的Web客户端  
✅ **保留终端输出**，保持原有开发习惯  
✅ 支持**自动重连**和**断线恢复**  

## 修改的文件

### 1. `config_ui.py` - 核心逻辑修改

#### 新增导入
```python
import queue
import asyncio
from fastapi import WebSocket, WebSocketDisconnect
from typing import List
```

#### 新增全局变量
```python
log_queue: queue.Queue = queue.Queue()
active_log_sockets: List[WebSocket] = []
broadcast_task: Optional[asyncio.Task] = None
reader_thread: Optional[threading.Thread] = None
```

#### 新增函数

**`log_reader_thread(process, q)`**
- 在独立线程中阻塞读取子进程的stdout
- 将每一行日志放入线程安全队列
- 同时打印到config_ui的stdout保留终端输出
- 进程结束时发送哨兵信号(None)

**`websocket_broadcaster(q)`**
- 常驻的asyncio任务
- 从队列异步获取日志行
- 广播到所有连接的WebSocket客户端
- 自动清理断开的连接

**`websocket_log_endpoint(websocket)`**
- FastAPI WebSocket端点 (`/ws/logs`)
- 接受和管理客户端连接
- 处理客户端断线事件

#### 修改的函数

**`start_service()`**
- 添加 `PYTHONUNBUFFERED=1` 环境变量，确保日志实时输出
- 启动日志读取线程
- 启动WebSocket广播任务

**`stop_service()`**
- 等待日志读取线程关闭
- 清空所有WebSocket连接

#### 新增端点

**`GET /logs.html`**
- 提供日志查看页面

---

### 2. `web_ui/logs.html` - 日志查看页面（新创建）

功能：
- 全屏日志查看器
- 实时显示日志内容
- 连接状态指示器（连接中/已连接/已断开）
- 自动滚动到底部选项
- 清空日志按钮
- 返回配置页链接

样式特点：
- 深色主题（`#0f172a` 背景）
- 等宽字体显示日志
- 使用 `<pre>` 标签保留日志格式
- 响应式设计

---

### 3. `web_ui/logs.js` - 日志前端脚本（新创建）

功能：
- 建立WebSocket连接到 `/ws/logs`
- 接收日志行并实时显示
- **自动重连**机制（指数退避，最多10秒）
- 连接状态管理和UI更新
- 自动滚动和清空日志功能

关键特性：
```javascript
// 连接状态状态类：connecting / connected / disconnected
// 重连延迟：1秒初始，最多10秒
// 支持HTTPS环境（自动检测 wss:// 协议）
```

---

### 4. `web_ui/config.html` - 侧边栏导航更新

新增导航菜单项：
```html
<a href="/logs.html" class="nav-item" data-section="logs">
    <span class="icon">📜</span>
    <span class="label">服务日志</span>
</a>
```

---

## 架构设计

```
┌─────────────────────────────────────────────────────────┐
│                    main.py (服务进程)                    │
│                  logger.info/error等                    │
│              ↓ stdout (日志行)                          │
├─────────────────────────────────────────────────────────┤
│                    config_ui.py                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │ log_reader_thread (同步)                         │   │
│  │ - 阻塞读取 process.stdout                        │   │
│  │ - print() → 保留终端输出                         │   │
│  │ - q.put(line) → 放入队列                         │   │
│  └──────────────────────────────────────────────────┘   │
│              ↓ log_queue (线程安全队列)                 │
│  ┌──────────────────────────────────────────────────┐   │
│  │ websocket_broadcaster (异步)                     │   │
│  │ - loop.run_in_executor(q.get) 异步读队列         │   │
│  │ - await ws.send_text(line) 广播日志              │   │
│  │ - 自动清理断开的连接                             │   │
│  └──────────────────────────────────────────────────┘   │
│              ↓ WebSocket /ws/logs                       │
├─────────────────────────────────────────────────────────┤
│            Web浏览器 (logs.html + logs.js)              │
│  ┌──────────────────────────────────────────────────┐   │
│  │ WebSocket Client                                │   │
│  │ - 连接 /ws/logs                                  │   │
│  │ - onmessage: 接收日志行                          │   │
│  │ - 显示到 <pre id="log-output">                   │   │
│  │ - 自动滚动/自动重连                              │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## 环境变量配置

启动 `main.py` 时自动设置：
```bash
PYTHONUNBUFFERED=1  # 禁用Python stdout缓冲，确保日志实时输出
```

## 使用步骤

1. **访问配置页面** → `http://localhost:8080/config.html`
2. **点击侧边栏** → "📜 服务日志" 菜单项
3. **进入日志页面** → 状态显示 "已连接"（绿色）
4. **启动或停止服务** → 从另一个标签页的配置页进行
5. **实时查看日志** → 日志页面自动显示所有输出
6. **网络中断** → 自动重连（指数退避）

## 测试场景

### 场景1：服务启动日志
1. 打开日志页面
2. 从配置页启动服务
3. 应看到 `WebSocket server started on ...` 等启动日志

### 场景2：AI对话日志
1. 连接WebSocket客户端到 `ws://localhost:8000`
2. 发送音频和请求
3. 日志页面实时显示 `audio_handler.py`, `service_manager.py` 的日志

### 场景3：断线重连
1. 停止 `config_ui.py` 服务
2. 日志页面显示 "已断开"（红色）
3. 重启 `config_ui.py`
4. 日志页面自动重连显示 "已连接"（绿色）

## 生产级特性

✅ **非阻塞I/O** - 日志线程独立，不影响主服务  
✅ **线程安全** - 使用queue.Queue确保安全性  
✅ **异步处理** - asyncio.to_thread避免阻塞事件循环  
✅ **自动重连** - 客户端断线自动重连（指数退避）  
✅ **错误处理** - UTF-8错误、连接异常都有处理  
✅ **终端兼容** - 保留原有终端日志输出  
✅ **多客户端** - 支持多个浏览器同时查看  
✅ **内存安全** - 自动清理断开的WebSocket连接  

## 后续可能的扩展

- 日志持久化存储（保存到文件）
- 日志级别过滤（INFO/WARNING/ERROR）
- 日志搜索和高亮功能
- 日志导出为文件
- 时间戳格式化显示
- 按模块分类显示日志

---

## 验证清单

- [x] `config_ui.py` 语法检查无错误
- [x] `logs.html` 和 `logs.js` 已创建
- [x] WebSocket端点 `/ws/logs` 已实现
- [x] 日志读取线程和广播任务已集成
- [x] 导航菜单已更新
- [x] 自动重连机制已实现
- [x] 终端输出保留
- [x] PYTHONUNBUFFERED 环境变量已设置

所有代码已准备就绪！🎉

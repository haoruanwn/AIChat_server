"""
AIChat Server 配置管理 UI
Web 界面用于配置 AI Persona、API 密钥等信息
支持启动、停止、重启 Python 服务
实现实时日志流式传输到 WebSocket 客户端
"""
import uvicorn
import json
import os
import subprocess
import signal
import time
import threading
import queue
import asyncio
from fastapi import FastAPI, Form, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, Dict, List
from tools.logger import logger

app = FastAPI(title="AIChat Server Configuration UI", version="2.0.0")
# 默认使用当前工作目录下的 ./config/config.json，允许通过 CONFIG_PATH 环境变量覆盖
_DEFAULT_CONFIG_PATH = os.path.abspath(os.path.join(os.getcwd(), "config", "config.json"))
CONFIG_FILE = os.environ.get("CONFIG_PATH", _DEFAULT_CONFIG_PATH)
CONFIG_DIR = os.path.dirname(CONFIG_FILE)

# ============ 全局变量：服务进程和日志管理 ============
service_process: Optional[subprocess.Popen] = None
service_lock = threading.Lock()

# [新增] 日志广播所需的全局变量
log_queue: queue.Queue = queue.Queue()
active_log_sockets: List[WebSocket] = []
broadcast_task: Optional[asyncio.Task] = None
reader_thread: Optional[threading.Thread] = None


# [新增] 日志读取线程函数
def log_reader_thread(process: subprocess.Popen, q: queue.Queue):
    """
    在一个单独的线程中读取子进程的stdout，并将其放入队列。
    这可以防止主进程的I/O阻塞。
    
    注意：这个线程会在进程关闭时自动退出，不需要等待。
    """
    try:
        # 逐行读取子进程的标准输出
        while True:
            line = process.stdout.readline()
            if not line:
                # 进程stdout已关闭
                logger.info("Log reader thread detected process stdout closed")
                break
            
            # 1. 保留在终端的输出 (打印到 config_ui 的 stdout)
            print(line, end='', flush=True)
            # 2. 放入队列，供WebSocket广播
            try:
                q.put(line, timeout=1.0)  # 1秒超时，避免队列满导致阻塞
            except queue.Full:
                logger.warning("Log queue is full, dropping oldest messages")
                try:
                    q.get_nowait()
                except queue.Empty:
                    pass
                q.put(line)
                
    except Exception as e:
        logger.error(f"Log reader thread error: {e}")
    finally:
        # 尝试发送哨兵信号，但不阻塞
        try:
            q.put(None, timeout=0.5)
        except queue.Full:
            pass  # 队列满，不强制等待


# [新增] WebSocket 广播任务
async def websocket_broadcaster(q: queue.Queue):
    """
    一个常驻的 asyncio 任务，从队列中获取日志并广播。
    使用超时避免卡顿。
    """
    loop = asyncio.get_event_loop()
    while True:
        try:
            # 使用超时的 queue.get 避免永久卡顿
            # 在 asyncio 中执行阻塞的 queue.get
            def get_with_timeout():
                try:
                    return q.get(timeout=1.0)  # 1秒超时
                except queue.Empty:
                    return None  # 队列空，返回 None
            
            line = await loop.run_in_executor(None, get_with_timeout)

            # 如果队列空超时，继续等待下一条消息
            if line is None:
                await asyncio.sleep(0.1)
                continue

            if not active_log_sockets:
                continue

            # [核心] 广播给所有连接的客户端
            # 我们复制列表以防在迭代时有客户端断开连接
            living_sockets = active_log_sockets[:]
            for ws in living_sockets:
                try:
                    await ws.send_text(line)
                except Exception:
                    # 客户端可能已断开，从主列表中移除
                    if ws in active_log_sockets:
                        active_log_sockets.remove(ws)

        except Exception as e:
            logger.error(f"Log broadcaster error: {e}")
            await asyncio.sleep(1)


# [新增] WebSocket 端点
@app.websocket("/ws/logs")
async def websocket_log_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_log_sockets.append(websocket)
    logger.info(f"Log client connected. Total clients: {len(active_log_sockets)}")
    try:
        while True:
            # 保持连接打开，等待断开
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("Log client disconnected.")
    finally:
        if websocket in active_log_sockets:
            active_log_sockets.remove(websocket)
        logger.info(f"Log client removed. Total clients: {len(active_log_sockets)}")

# ============ Pydantic 模型 ============

class AIPersonaConfig(BaseModel):
    """AI Persona 配置模型"""
    bot_name: str = "Echo"
    system_content: str = "你是一个桌面机器人，名为Echo，友好简洁地回答用户问题。"

class FullConfig(BaseModel):
    """完整的配置模型"""
    ACCESS_TOKEN: str = "123456"
    ALIYUN_API_KEY: str
    CHAT_MODEL: str = "qwen-turbo"
    INTENT_MODEL: str = "qwen-turbo"
    SYSTEM_PROMPT: str = "你是一个桌面机器人，名为Echo，友好简洁地回答用户问题。"
    ASR_DEVICE: str = "cpu"
    VAD_DEVICE: str = "cpu"
    API_TIMEOUT: int = 10
    ai_persona: Optional[AIPersonaConfig] = None

# ============ 静态文件服务 ============
static_dir = os.path.join(os.path.dirname(__file__), "web_ui")
if os.path.exists(static_dir):
    try:
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
        logger.info(f"Static files mounted from {static_dir}")
    except Exception as e:
        logger.warning(f"Failed to mount static files: {e}")

# ============ 服务进程管理函数 ============

def start_service():
    """启动 Python 主服务"""
    global service_process, broadcast_task, reader_thread

    with service_lock:
        if service_process and service_process.poll() is None:
            logger.warning("Service is already running")
            return {"success": False, "message": "服务已在运行"}

        try:
            logger.info("Starting AIChat main service...")

            # [修改] 强制Python使用非缓冲的标准输出
            env = os.environ.copy()
            env['PYTHONUNBUFFERED'] = '1'

            service_process = subprocess.Popen(
                ["python", "./main.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,  # 行缓冲
                encoding='utf-8',
                errors='replace',  # 避免UTF-8解码错误
                env=env  # [修改] 传入环境变量
            )

            # [新增] 启动日志读取线程
            reader_thread = threading.Thread(
                target=log_reader_thread,
                args=(service_process, log_queue),
                daemon=True
            )
            reader_thread.start()

            # [新增] 启动WebSocket广播任务 (如果它还没运行)
            if broadcast_task is None or broadcast_task.done():
                loop = asyncio.get_event_loop()
                broadcast_task = loop.create_task(websocket_broadcaster(log_queue))
                logger.info("Log broadcaster task started.")

            time.sleep(1)  # 给子进程一点启动时间

            if service_process.poll() is None:
                logger.info(f"Service started successfully (PID: {service_process.pid})")
                return {"success": True, "message": "服务已启动"}
            else:
                error_msg = f"服务启动失败，退出码: {service_process.poll()}"
                logger.error(error_msg)
                return {"success": False, "message": error_msg}

        except Exception as e:
            error_msg = f"Failed to start service: {e}"
            logger.error(error_msg)
            return {"success": False, "message": error_msg}

def stop_service():
    """停止 Python 主服务"""
    global service_process, broadcast_task, reader_thread

    with service_lock:
        if not service_process or service_process.poll() is not None:
            logger.warning("Service is not running")
            return {"success": False, "message": "服务未运行"}

        try:
            logger.info("Stopping AIChat service...")
            service_process.terminate()  # 发送 SIGTERM

            # 等待进程结束，超时 5 秒后强制杀死
            try:
                service_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("Service did not stop gracefully, killing it...")
                service_process.kill()
                service_process.wait()

            service_process = None
            logger.info("Service stopped successfully")

            # [新增] 停止相关任务
            # 停止日志读取线程 (它会在 process.stdout 关闭时自动退出)
            if reader_thread and reader_thread.is_alive():
                logger.info("Waiting for log reader thread to stop...")
                reader_thread.join(timeout=2)

            # [新增] 断开所有日志客户端连接
            for ws in active_log_sockets[:]:
                try:
                    # 无法在同步函数中调用 async 方法，改用循环中处理
                    pass
                except:
                    pass
            active_log_sockets.clear()

            return {"success": True, "message": "服务已停止"}

        except Exception as e:
            error_msg = f"Failed to stop service: {e}"
            logger.error(error_msg)
            return {"success": False, "message": error_msg}

def get_service_status():
    """获取服务状态"""
    global service_process
    
    if service_process is None or service_process.poll() is not None:
        return {
            "running": False,
            "status": "stopped",
            "message": "服务未运行"
        }
    else:
        return {
            "running": True,
            "status": "running",
            "message": "服务正在运行",
            "pid": service_process.pid
        }

# ============ REST API 端点 ============

@app.get("/api/config")
async def get_config():
    """获取当前配置"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # 隐藏 API Key 的中间部分
                if "ALIYUN_API_KEY" in config and config["ALIYUN_API_KEY"]:
                    api_key = config["ALIYUN_API_KEY"]
                    if len(api_key) > 8:
                        config["ALIYUN_API_KEY"] = api_key[:3] + "*" * (len(api_key) - 7) + api_key[-4:]
                    else:
                        config["ALIYUN_API_KEY"] = "*" * len(api_key)
                return {"success": True, "data": config}
        else:
            # 返回默认配置
            return {"success": True, "data": {
                "ACCESS_TOKEN": "123456",
                "ALIYUN_API_KEY": "",
                "CHAT_MODEL": "qwen-turbo",
                "INTENT_MODEL": "qwen-turbo",
                "SYSTEM_PROMPT": "你是一个桌面机器人，名为Echo，友好简洁地回答用户问题。",
                "ASR_DEVICE": "cpu",
                "VAD_DEVICE": "cpu",
                "API_TIMEOUT": 10,
                "ai_persona": {
                    "bot_name": "Echo",
                    "system_content": "你是一个桌面机器人，名为Echo，友好简洁地回答用户问题。"
                }
            }}
    except Exception as e:
        logger.error(f"Failed to get config: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/config")
async def save_config(config: FullConfig):
    """保存配置到 JSON 文件"""
    try:
        # 确保 /config 目录存在
        os.makedirs(CONFIG_DIR, exist_ok=True)
        
        config_data = config.model_dump()
        
        # 如果 API Key 被隐藏（包含 *），从现有配置恢复
        if config_data.get("ALIYUN_API_KEY", "") and "*" in config_data.get("ALIYUN_API_KEY", ""):
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    try:
                        old_config = json.load(f)
                        config_data["ALIYUN_API_KEY"] = old_config.get("ALIYUN_API_KEY", "")
                    except:
                        pass
        
        # 确保 ai_persona 存在
        if not config_data.get("ai_persona"):
            config_data["ai_persona"] = {
                "bot_name": "Echo",
                "system_content": "你是一个桌面机器人，名为Echo，友好简洁地回答用户问题。"
            }
        
        # 写入文件
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=4, ensure_ascii=False)
        
        logger.info(f"Configuration saved to {CONFIG_FILE}")
        
        # 隐藏返回数据中的敏感信息
        return_data = config_data.copy()
        if "ALIYUN_API_KEY" in return_data and return_data["ALIYUN_API_KEY"]:
            api_key = return_data["ALIYUN_API_KEY"]
            if len(api_key) > 8:
                return_data["ALIYUN_API_KEY"] = api_key[:3] + "*" * (len(api_key) - 7) + api_key[-4:]
            else:
                return_data["ALIYUN_API_KEY"] = "*" * len(api_key)
        
        return {
            "success": True,
            "message": "配置已保存",
            "data": return_data
        }
    
    except Exception as e:
        logger.error(f"Failed to save config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save config: {e}")

# ============ 服务生命周期管理 API ============

@app.get("/api/service/status")
async def get_service_status_endpoint():
    """获取服务状态"""
    return get_service_status()

@app.post("/api/service/start")
async def start_service_endpoint():
    """启动服务"""
    result = start_service()
    # 将结果与状态信息合并
    status = get_service_status()
    result.update(status)
    return result

@app.post("/api/service/stop")
async def stop_service_endpoint():
    """停止服务"""
    result = stop_service()
    status = get_service_status()
    result.update(status)
    return result

@app.post("/api/service/restart")
async def restart_service_endpoint():
    """只重启 AI 聊天服务（子进程），不停止 Web 服务器"""
    global service_process
    
    try:
        with service_lock:
            if not service_process or service_process.poll() is not None:
                logger.warning("Service is not running, starting it...")
                result = start_service()
                status = get_service_status()
                return {
                    "success": result.get("success", False),
                    "message": "服务已启动",
                    **status
                }
            
            # 只重启子进程，不停止 Web 服务器
            logger.info("Restarting AIChat service (graceful restart)...")
            
            # 1. 停止子进程（不等待日志读取线程）
            old_process = service_process
            service_process = None  # 立即清空引用，避免其他操作使用旧进程
            
            old_process.terminate()  # 发送 SIGTERM
            try:
                # 给进程短暂时间优雅关闭（2秒）
                old_process.wait(timeout=2)
                logger.info("Service process stopped gracefully")
            except subprocess.TimeoutExpired:
                logger.warning("Service did not stop gracefully, killing it...")
                old_process.kill()
                old_process.wait()
            
            # 不等待日志读取线程 - 它会自动在检测到进程关闭时退出
            # 这避免了重启时的长等待
            
            time.sleep(0.2)  # 短暂延迟，确保资源释放
            
            # 2. 启动新的子进程
            result = start_service()
            status = get_service_status()
            
            logger.info(f"Service restart completed: {result['message']}")
            
            return {
                "success": result.get("success", False),
                "message": "AI 聊天服务已重启（WebSocket 连接保持）",
                **status
            }
    except Exception as e:
        logger.error(f"Failed to restart service: {e}")
        return {
            "success": False,
            "message": f"重启失败: {e}",
            **get_service_status()
        }

@app.get("/api/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "ok",
        "service": "AIChat Configuration UI",
        "config_file": CONFIG_FILE,
        "config_exists": os.path.exists(CONFIG_FILE),
        "service_status": get_service_status()
    }

# ============ Web UI 页面路由 ============

@app.get("/", response_class=HTMLResponse)
async def index():
    """主配置管理页面：优先返回 `web_ui/config.html` 静态文件。"""
    config_html_path = os.path.join(static_dir, "config.html")
    if os.path.exists(config_html_path):
        return FileResponse(config_html_path, media_type='text/html')
    else:
        # 如果静态文件不存在，返回一个简洁的说明页面
        return HTMLResponse("""
            <html>
              <head><meta charset='utf-8'><title>AIChat Configuration UI</title></head>
              <body style='font-family: system-ui, -apple-system, Roboto, "Helvetica Neue", Arial; padding:40px;'>
                <h2>配置界面未找到</h2>
                <p>请确保目录 <code>web_ui/config.html</code> 存在，或将静态文件放到 <code>web_ui/</code>。</p>
              </body>
            </html>
        """)

@app.get("/config.html", response_class=HTMLResponse)
async def config_html():
    """配置管理页面"""
    return await index()


if __name__ == "__main__":
    logger.info("Starting AIChat Configuration UI server on port 8080...")
    logger.info("Web UI available at: http://localhost:8080")
    uvicorn.run(app, host="0.0.0.0", port=8080)

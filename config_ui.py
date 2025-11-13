"""
AIChat Server 配置管理 UI
Web 界面用于配置 AI Persona、API 密钥等信息
支持启动、停止、重启 Python 服务
"""
import uvicorn
import json
import os
import subprocess
import signal
import time
import threading
from fastapi import FastAPI, Form, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, Dict
from tools.logger import logger

app = FastAPI(title="AIChat Server Configuration UI", version="2.0.0")
# 默认使用当前工作目录下的 ./config/config.json，允许通过 CONFIG_PATH 环境变量覆盖
_DEFAULT_CONFIG_PATH = os.path.abspath(os.path.join(os.getcwd(), "config", "config.json"))
CONFIG_FILE = os.environ.get("CONFIG_PATH", _DEFAULT_CONFIG_PATH)
CONFIG_DIR = os.path.dirname(CONFIG_FILE)

# ============ 全局变量：服务进程管理 ============
service_process: Optional[subprocess.Popen] = None
service_lock = threading.Lock()

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
    global service_process
    
    with service_lock:
        if service_process and service_process.poll() is None:
            logger.warning("Service is already running")
            return {"success": False, "message": "服务已在运行"}
        
        try:
            logger.info("Starting AIChat main service...")
            # 启动 main.py
            service_process = subprocess.Popen(
                ["python", "./main.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            # 给服务一点时间启动
            time.sleep(2)
            
            if service_process.poll() is None:
                logger.info("Service started successfully")
                return {"success": True, "message": "服务已启动"}
            else:
                error_msg = "服务启动失败"
                logger.error(error_msg)
                return {"success": False, "message": error_msg}
                
        except Exception as e:
            error_msg = f"Failed to start service: {e}"
            logger.error(error_msg)
            return {"success": False, "message": error_msg}

def stop_service():
    """停止 Python 主服务"""
    global service_process
    
    with service_lock:
        if not service_process or service_process.poll() is not None:
            logger.warning("Service is not running")
            return {"success": False, "message": "服务未运行"}
        
        try:
            logger.info("Stopping AIChat service...")
            service_process.terminate()
            
            # 等待进程结束，超时 5 秒后强制杀死
            try:
                service_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("Service did not stop gracefully, killing it...")
                service_process.kill()
                service_process.wait()
            
            service_process = None
            logger.info("Service stopped successfully")
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
    """重启服务"""
    try:
        stop_result = stop_service()
        time.sleep(1)
        start_result = start_service()
        
        status = get_service_status()
        return {
            "success": start_result.get("success", False),
            "message": "服务已重启",
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

# 已将前端资源移至 web_ui/ 目录，默认静态文件由 FastAPI 的 StaticFiles 提供（见上方挂载）

if __name__ == "__main__":
    logger.info("Starting AIChat Configuration UI server on port 8080...")
    logger.info("Web UI available at: http://localhost:8080")
    uvicorn.run(app, host="0.0.0.0", port=8080)

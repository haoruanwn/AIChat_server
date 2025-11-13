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
    """主配置管理页面"""
    config_html_path = os.path.join(static_dir, "config.html")
    if os.path.exists(config_html_path):
        with open(config_html_path, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        return get_default_config_page()

@app.get("/config.html", response_class=HTMLResponse)
async def config_html():
    """配置管理页面"""
    return await index()

def get_default_config_page():
    """返回默认配置管理页面（HTML）"""
    return """
    <!DOCTYPE html>
    <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>AIChat Server 配置管理</title>
            <style>
                * {
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }
                
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
                        'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    padding: 20px;
                }
                
                .container {
                    max-width: 1000px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 12px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    overflow: hidden;
                }
                
                .header {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                }
                
                .header h1 {
                    font-size: 32px;
                    margin-bottom: 10px;
                }
                
                .header p {
                    font-size: 14px;
                    opacity: 0.9;
                }
                
                .content {
                    padding: 30px;
                }
                
                .section {
                    margin-bottom: 30px;
                }
                
                .section-title {
                    font-size: 18px;
                    font-weight: 600;
                    color: #333;
                    margin-bottom: 15px;
                    padding-bottom: 10px;
                    border-bottom: 2px solid #ddd;
                }
                
                .form-group {
                    margin-bottom: 15px;
                }
                
                label {
                    display: block;
                    color: #333;
                    font-weight: 500;
                    margin-bottom: 8px;
                    font-size: 14px;
                }
                
                input[type="text"],
                input[type="password"],
                input[type="number"],
                textarea,
                select {
                    width: 100%;
                    padding: 10px 12px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    font-size: 14px;
                    font-family: inherit;
                    transition: border-color 0.3s;
                }
                
                input[type="text"]:focus,
                input[type="password"]:focus,
                input[type="number"]:focus,
                textarea:focus,
                select:focus {
                    outline: none;
                    border-color: #667eea;
                    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
                }
                
                textarea {
                    resize: vertical;
                    min-height: 100px;
                    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
                }
                
                .button-group {
                    display: flex;
                    gap: 10px;
                    flex-wrap: wrap;
                    margin-top: 20px;
                }
                
                button {
                    padding: 10px 20px;
                    font-size: 14px;
                    font-weight: 600;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                    transition: all 0.3s;
                    min-width: 120px;
                }
                
                button:disabled {
                    opacity: 0.5;
                    cursor: not-allowed;
                }
                
                .btn-primary {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                }
                
                .btn-primary:hover:not(:disabled) {
                    transform: translateY(-2px);
                    box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
                }
                
                .btn-success {
                    background: #27ae60;
                    color: white;
                }
                
                .btn-success:hover:not(:disabled) {
                    background: #229954;
                    transform: translateY(-2px);
                }
                
                .btn-warning {
                    background: #f39c12;
                    color: white;
                }
                
                .btn-warning:hover:not(:disabled) {
                    background: #e67e22;
                    transform: translateY(-2px);
                }
                
                .btn-danger {
                    background: #e74c3c;
                    color: white;
                }
                
                .btn-danger:hover:not(:disabled) {
                    background: #c0392b;
                    transform: translateY(-2px);
                }
                
                .btn-secondary {
                    background: #95a5a6;
                    color: white;
                }
                
                .btn-secondary:hover:not(:disabled) {
                    background: #7f8c8d;
                }
                
                .status-badge {
                    display: inline-block;
                    padding: 6px 12px;
                    border-radius: 20px;
                    font-size: 12px;
                    font-weight: 600;
                    margin-left: 10px;
                }
                
                .status-running {
                    background: #d5f4e6;
                    color: #27ae60;
                }
                
                .status-stopped {
                    background: #fadbd8;
                    color: #e74c3c;
                }
                
                .alert {
                    padding: 12px 15px;
                    border-radius: 4px;
                    margin-bottom: 20px;
                    font-size: 14px;
                    animation: slideIn 0.3s ease-in-out;
                }
                
                .alert-success {
                    background: #d5f4e6;
                    color: #27ae60;
                    border-left: 4px solid #27ae60;
                }
                
                .alert-error {
                    background: #fadbd8;
                    color: #e74c3c;
                    border-left: 4px solid #e74c3c;
                }
                
                .alert-info {
                    background: #d6eaf8;
                    color: #2980b9;
                    border-left: 4px solid #2980b9;
                }
                
                .hint {
                    font-size: 12px;
                    color: #999;
                    margin-top: 5px;
                }
                
                .hint a {
                    color: #667eea;
                    text-decoration: none;
                }
                
                .hint a:hover {
                    text-decoration: underline;
                }
                
                .row {
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 20px;
                }
                
                @media (max-width: 768px) {
                    .row {
                        grid-template-columns: 1fr;
                    }
                    
                    .header h1 {
                        font-size: 24px;
                    }
                }
                
                @keyframes slideIn {
                    from {
                        opacity: 0;
                        transform: translateY(-10px);
                    }
                    to {
                        opacity: 1;
                        transform: translateY(0);
                    }
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>⚙️ AIChat Server 配置管理</h1>
                    <p>配置 AI 机器人、API 密钥和服务参数</p>
                </div>
                
                <div class="content">
                    <!-- 消息提示区 -->
                    <div id="message-area"></div>
                    
                    <!-- 服务状态 -->
                    <div class="section">
                        <div class="section-title">
                            🔌 服务状态
                            <span id="status-badge" class="status-badge status-stopped">未运行</span>
                        </div>
                        <div class="button-group">
                            <button class="btn-success" id="btn-start" onclick="startService()">▶️ 启动服务</button>
                            <button class="btn-warning" id="btn-restart" onclick="restartService()" disabled>🔄 重启服务</button>
                            <button class="btn-danger" id="btn-stop" onclick="stopService()" disabled>⏹️ 停止服务</button>
                        </div>
                        <p id="service-message" class="hint" style="margin-top: 10px;"></p>
                    </div>
                    
                    <!-- 配置表单 -->
                    <form id="config-form">
                        <!-- API 配置 -->
                        <div class="section">
                            <div class="section-title">🔑 API 配置</div>
                            
                            <div class="form-group">
                                <label for="ACCESS_TOKEN">访问令牌 (ACCESS_TOKEN)</label>
                                <input type="text" id="ACCESS_TOKEN" name="ACCESS_TOKEN" placeholder="客户端连接时验证的令牌">
                                <div class="hint">客户端连接时需要提供此令牌进行验证</div>
                            </div>
                            
                            <div class="form-group">
                                <label for="ALIYUN_API_KEY">阿里云 API Key <span style="color: #e74c3c;">*</span></label>
                                <input type="password" id="ALIYUN_API_KEY" name="ALIYUN_API_KEY" placeholder="sk-xxxxxxxxxxxxx" required>
                                <div class="hint">从 <a href="https://bailian.console.aliyun.com/" target="_blank">阿里云控制台</a> 获取</div>
                            </div>
                        </div>
                        
                        <!-- AI 配置 -->
                        <div class="section">
                            <div class="section-title">🤖 AI 配置</div>
                            
                            <div class="row">
                                <div class="form-group">
                                    <label for="bot_name">机器人名称</label>
                                    <input type="text" id="bot_name" name="bot_name" placeholder="例如：Echo" value="Echo">
                                    <div class="hint">机器人的名字，用于标识</div>
                                </div>
                                
                                <div class="form-group">
                                    <label for="CHAT_MODEL">聊天模型 (CHAT_MODEL)</label>
                                    <select id="CHAT_MODEL" name="CHAT_MODEL">
                                        <option value="qwen-turbo">qwen-turbo（推荐）</option>
                                        <option value="qwen-plus">qwen-plus</option>
                                        <option value="qwen-long">qwen-long</option>
                                        <option value="qwen-max">qwen-max</option>
                                    </select>
                                    <div class="hint">用于对话的大模型</div>
                                </div>
                            </div>
                            
                            <div class="row">
                                <div class="form-group">
                                    <label for="INTENT_MODEL">意图识别模型 (INTENT_MODEL)</label>
                                    <select id="INTENT_MODEL" name="INTENT_MODEL">
                                        <option value="qwen-turbo">qwen-turbo（推荐）</option>
                                        <option value="qwen-plus">qwen-plus</option>
                                        <option value="qwen-long">qwen-long</option>
                                    </select>
                                    <div class="hint">用于识别用户意图</div>
                                </div>
                                
                                <div class="form-group">
                                    <label for="API_TIMEOUT">API 超时时间 (秒)</label>
                                    <input type="number" id="API_TIMEOUT" name="API_TIMEOUT" min="1" max="120" value="10">
                                    <div class="hint">API 调用超时时间</div>
                                </div>
                            </div>
                            
                            <div class="form-group">
                                <label for="system_content">系统提示词 (SYSTEM_PROMPT)</label>
                                <textarea id="system_content" name="system_content" placeholder="你是一个..."></textarea>
                                <div class="hint">定义 AI 助手的角色、性格和行为规范</div>
                            </div>
                        </div>
                        
                        <!-- 硬件配置 -->
                        <div class="section">
                            <div class="section-title">💻 硬件配置</div>
                            
                            <div class="row">
                                <div class="form-group">
                                    <label for="ASR_DEVICE">ASR 设备 (语音识别)</label>
                                    <select id="ASR_DEVICE" name="ASR_DEVICE">
                                        <option value="cpu">CPU</option>
                                        <option value="cuda">CUDA (GPU)</option>
                                    </select>
                                    <div class="hint">语音识别模型运行设备</div>
                                </div>
                                
                                <div class="form-group">
                                    <label for="VAD_DEVICE">VAD 设备 (语音检测)</label>
                                    <select id="VAD_DEVICE" name="VAD_DEVICE">
                                        <option value="cpu">CPU</option>
                                        <option value="cuda">CUDA (GPU)</option>
                                    </select>
                                    <div class="hint">语音活动检测模型运行设备</div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- 操作按钮 -->
                        <div class="section">
                            <div class="button-group">
                                <button type="submit" class="btn-primary">💾 保存配置</button>
                                <button type="reset" class="btn-secondary">🔄 重置</button>
                            </div>
                        </div>
                    </form>
                </div>
            </div>
            
            <script>
                const CONFIG_API = "/api/config";
                const SERVICE_API = "/api/service";
                
                // ============ 初始化 ============
                window.addEventListener('load', async () => {
                    await loadConfig();
                    await updateServiceStatus();
                    // 每 2 秒更新一次服务状态
                    setInterval(updateServiceStatus, 2000);
                });
                
                // ============ 加载配置 ============
                async function loadConfig() {
                    try {
                        const response = await fetch(CONFIG_API);
                        const result = await response.json();
                        
                        if (result.success && result.data) {
                            const data = result.data;
                            document.getElementById('ACCESS_TOKEN').value = data.ACCESS_TOKEN || '';
                            document.getElementById('ALIYUN_API_KEY').value = data.ALIYUN_API_KEY || '';
                            document.getElementById('CHAT_MODEL').value = data.CHAT_MODEL || 'qwen-turbo';
                            document.getElementById('INTENT_MODEL').value = data.INTENT_MODEL || 'qwen-turbo';
                            document.getElementById('API_TIMEOUT').value = data.API_TIMEOUT || 10;
                            document.getElementById('system_content').value = data.SYSTEM_PROMPT || '';
                            document.getElementById('ASR_DEVICE').value = data.ASR_DEVICE || 'cpu';
                            document.getElementById('VAD_DEVICE').value = data.VAD_DEVICE || 'cpu';
                            
                            if (data.ai_persona) {
                                document.getElementById('bot_name').value = data.ai_persona.bot_name || 'Echo';
                            }
                        }
                    } catch (error) {
                        console.error('Failed to load config:', error);
                        showMessage('加载配置失败', 'error');
                    }
                }
                
                // ============ 保存配置 ============
                document.getElementById('config-form').addEventListener('submit', async (e) => {
                    e.preventDefault();
                    
                    const formData = {
                        ACCESS_TOKEN: document.getElementById('ACCESS_TOKEN').value,
                        ALIYUN_API_KEY: document.getElementById('ALIYUN_API_KEY').value,
                        CHAT_MODEL: document.getElementById('CHAT_MODEL').value,
                        INTENT_MODEL: document.getElementById('INTENT_MODEL').value,
                        SYSTEM_PROMPT: document.getElementById('system_content').value,
                        ASR_DEVICE: document.getElementById('ASR_DEVICE').value,
                        VAD_DEVICE: document.getElementById('VAD_DEVICE').value,
                        API_TIMEOUT: parseInt(document.getElementById('API_TIMEOUT').value),
                        ai_persona: {
                            bot_name: document.getElementById('bot_name').value,
                            system_content: document.getElementById('system_content').value
                        }
                    };
                    
                    try {
                        const response = await fetch(CONFIG_API, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify(formData)
                        });
                        
                        const result = await response.json();
                        
                        if (result.success) {
                            showMessage('✅ 配置已保存', 'success');
                            // 如果服务在运行，提示用户可以重启
                            if (document.getElementById('btn-restart').disabled === false) {
                                showMessage('💡 配置已保存，可点击"重启服务"应用更改', 'info');
                            }
                        } else {
                            showMessage('❌ 保存失败: ' + (result.error || '未知错误'), 'error');
                        }
                    } catch (error) {
                        console.error('Failed to save config:', error);
                        showMessage('❌ 保存配置失败', 'error');
                    }
                });
                
                // ============ 服务管理 ============
                async function updateServiceStatus() {
                    try {
                        const response = await fetch(SERVICE_API + "/status");
                        const result = await response.json();
                        
                        const badge = document.getElementById('status-badge');
                        const message = document.getElementById('service-message');
                        const startBtn = document.getElementById('btn-start');
                        const restartBtn = document.getElementById('btn-restart');
                        const stopBtn = document.getElementById('btn-stop');
                        
                        if (result.running) {
                            badge.textContent = '✅ 运行中';
                            badge.className = 'status-badge status-running';
                            message.textContent = `PID: ${result.pid}`;
                            startBtn.disabled = true;
                            restartBtn.disabled = false;
                            stopBtn.disabled = false;
                        } else {
                            badge.textContent = '⏹️ 已停止';
                            badge.className = 'status-badge status-stopped';
                            message.textContent = result.message;
                            startBtn.disabled = false;
                            restartBtn.disabled = true;
                            stopBtn.disabled = true;
                        }
                    } catch (error) {
                        console.error('Failed to get service status:', error);
                    }
                }
                
                async function startService() {
                    try {
                        const response = await fetch(SERVICE_API + "/start", { method: 'POST' });
                        const result = await response.json();
                        
                        if (result.success) {
                            showMessage('✅ 服务已启动', 'success');
                        } else {
                            showMessage('❌ 启动失败: ' + result.message, 'error');
                        }
                        await updateServiceStatus();
                    } catch (error) {
                        console.error('Failed to start service:', error);
                        showMessage('❌ 启动服务失败', 'error');
                    }
                }
                
                async function stopService() {
                    if (!confirm('确定要停止服务吗？')) return;
                    
                    try {
                        const response = await fetch(SERVICE_API + "/stop", { method: 'POST' });
                        const result = await response.json();
                        
                        if (result.success) {
                            showMessage('✅ 服务已停止', 'success');
                        } else {
                            showMessage('❌ 停止失败: ' + result.message, 'error');
                        }
                        await updateServiceStatus();
                    } catch (error) {
                        console.error('Failed to stop service:', error);
                        showMessage('❌ 停止服务失败', 'error');
                    }
                }
                
                async function restartService() {
                    try {
                        const response = await fetch(SERVICE_API + "/restart", { method: 'POST' });
                        const result = await response.json();
                        
                        if (result.success) {
                            showMessage('✅ 服务已重启', 'success');
                        } else {
                            showMessage('❌ 重启失败: ' + result.message, 'error');
                        }
                        await updateServiceStatus();
                    } catch (error) {
                        console.error('Failed to restart service:', error);
                        showMessage('❌ 重启服务失败', 'error');
                    }
                }
                
                // ============ 消息提示 ============
                function showMessage(message, type = 'info') {
                    const messageArea = document.getElementById('message-area');
                    const alertDiv = document.createElement('div');
                    alertDiv.className = 'alert alert-' + type;
                    alertDiv.textContent = message;
                    
                    messageArea.appendChild(alertDiv);
                    
                    setTimeout(() => {
                        alertDiv.remove();
                    }, 5000);
                }
            </script>
        </body>
    </html>
    """

if __name__ == "__main__":
    logger.info("Starting AIChat Configuration UI server on port 8080...")
    logger.info("Web UI available at: http://localhost:8080")
    uvicorn.run(app, host="0.0.0.0", port=8080)

import json
import os
import dashscope
from tools.logger import logger

class Settings:
    def __init__(self):
        # 1. 设置默认值
        self.ACCESS_TOKEN = "123456"
        self.DEVICE_ID = "00:11:22:33:44:55"
        self.PROTOCOL_VERSION = 2
        
        self.ALIYUN_API_KEY = None  # 将从配置加载
        
        # 模型选择
        self.INTENT_MODEL = "qwen-turbo"       # 专门用于意图识别
        self.CHAT_MODEL = "qwen-turbo"         # 用于常规对话
        self.SYSTEM_PROMPT = "你是一个桌面机器人，名为Echo，友好简洁地回答用户问题。"

        # device
        self.ASR_DEVICE = "cpu"            # ASR 模型使用的设备
        self.VAD_DEVICE = "cpu"            # VAD 模型使用的设备
        
        # 其他模型配置
        self.VAD_MODEL_PATH = "models/FunAudioLLM/iic/speech_fsmn_vad_zh-cn-16k-common-pytorch"

        # 超时设置
        self.API_TIMEOUT = 10  # 秒
        
        # AI Persona 配置 - 只有 Echo 的默认人设
        self.ai_persona = {
            "bot_name": "Echo",
            "system_content": "你是一个桌面机器人，名为Echo，友好简洁地回答用户问题。"
        }

    def load_from_json(self, config_path: str):
        """从 JSON 文件加载配置并覆盖默认值"""
        try:
            if os.path.exists(config_path):
                logger.info(f"Loading configuration from {config_path}")
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    
                    # 动态更新所有属性
                    for key, value in config_data.items():
                        if hasattr(self, key):
                            setattr(self, key, value)
                            # 隐藏 API Key 等敏感信息
                            display_value = '*' * 8 if 'KEY' in key.upper() else value
                            logger.info(f"Loaded config: {key} = {display_value}")
                        else:
                            logger.warning(f"Unknown config key in {config_path}: {key}")
                            
                # 特殊处理：设置 dashscope.api_key
                if self.ALIYUN_API_KEY:
                    dashscope.api_key = self.ALIYUN_API_KEY
                    logger.info("Dashscope API key has been configured.")
                else:
                    logger.warning("ALIYUN_API_KEY not found in config. Dashscope API key is not set.")
                
            else:
                logger.warning(f"Config file not found: {config_path}. Using default settings.")
        
        except Exception as e:
            logger.error(f"Failed to load config from {config_path}: {e}")
            raise

    def Set_API_Key(self, api_key: str):
        """设置 API Key (保留此方法以向后兼容)"""
        logger.warning("Set_API_Key() is deprecated. Use ALIYUN_API_KEY in config.json instead.")
        if api_key:
            dashscope.api_key = api_key
            self.ALIYUN_API_KEY = api_key

# 创建全局单例
global_settings = Settings()

# !!! 关键：定义配置文件路径
CONFIG_FILE_PATH = os.environ.get("CONFIG_PATH", "/config/config.json")

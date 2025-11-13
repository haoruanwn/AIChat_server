from typing import List, Dict, Optional
from config.settings import global_settings
from tools.logger import logger
from models.llm_model import LLMModel

class ChatService:
    def __init__(self):
        # dashscope.api_key = settings.DASHSCOPE_API_KEY
        self.chat_llm_model = LLMModel(model_name=global_settings.CHAT_MODEL)
        self.chat_llm_model.clear_messages()
        # 使用 global_settings 中的系统提示词
        self.chat_llm_model.set_model_sys_content(global_settings.SYSTEM_PROMPT)

    def chat_clear(self):
        """清除对话历史记录"""
        self.chat_llm_model.clear_messages()

    def generate_chat_response(self, user_input: str, history: Optional[Dict] = None, is_stream: bool = False) -> str:
        """使用通用模型生成对话回复"""
        if history:
            for his in history:
                if "role" in his and "content" in his:
                    self.chat_llm_model.add_message(his["role"], his["content"])
        if is_stream:
            # 流式生成回答
            return self.chat_llm_model.get_LLM_response_stream(user_input)
        # 非流式生成回答
        else:
            return self.chat_llm_model.get_LLM_response(user_input)


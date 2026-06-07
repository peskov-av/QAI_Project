"""
LLM Client - Модуль для взаимодействия с Gemini LLM
"""
import os
import logging
import google.generativeai as genai
from typing import Optional
from qa_pipeline.config import CONFIG

logger = logging.getLogger(__name__)

class LLMClient:
    """
    Клиент для взаимодействия с Google Gemini API.
    """

    def __init__(self):
        api_key = CONFIG.llm.api_key
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is not set")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(CONFIG.llm.model_name)
        logger.info(f"LLMClient initialized with model: {CONFIG.llm.model_name}")

    def generate(self, prompt: str) -> str:
        """
        Генерация текста с помощью LLM

        Args:
            prompt: Запрос для LLM

        Returns:
            Ответ от LLM
        """
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=CONFIG.llm.temperature,
                    max_output_tokens=CONFIG.llm.max_output_tokens,
                )
            )
            return response.text
        except Exception as e:
            logger.error(f"Error generating content: {e}")
            raise

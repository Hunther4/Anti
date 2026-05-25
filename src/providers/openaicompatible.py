"""
OpenAI Compatible Provider - Permite conectar cualquier LLM con API compatible (OpenAI, Anyscale, Together, Groq, etc.)

Requiere en config.json:
- provider: "openaicompatible"
- openaicompatible_url: "https://api.groq.com/openai/v1"
- openaicompatible_model: "llama3-8b-8192"
- openaicompatible_api_key: "gsk_..."
"""

import requests
import os
import logging
import asyncio
import time
from typing import List, Dict, Tuple, Any

from .base import BaseProvider

logger = logging.getLogger(__name__)


class OpenAICompatibleProvider(BaseProvider):
    """Proveedor genérico compatible con OpenAI."""
    
    def __init__(self, base_url: str = None, model: str = None, timeout: int = 180, api_key: str = None):
        super().__init__(
            base_url=base_url or "http://localhost:8000/v1", 
            model=model or "custom-model",
            timeout=timeout
        )
        self.api_key = api_key or ""
        
        if not self.api_key:
            logger.warning("[OpenAICompatible] API key no configurada")
    
    async def chat(self, messages: List[Dict], temperature: float = 0.7) -> Tuple[str, Dict[str, Any]]:
        """Envía un chat al endpoint compatible."""
        return await asyncio.to_thread(self._chat_sync, messages, temperature)

    def _chat_sync(self, messages: List[Dict], temperature: float = 0.7) -> Tuple[str, Dict[str, Any]]:
        start_time = time.time()
        url = f"{self.base_url}/chat/completions"
        
        headers = {
            "Content-Type": "application/json"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": False
        }
        
        last_error = None
        for attempt in range(self.max_retries):
            try:
                session = self.get_session()
                response = session.post(
                    url, 
                    json=payload, 
                    headers=headers,
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                data = response.json()
                content = data['choices'][0]['message']['content']
                duration = time.time() - start_time
                
                usage_raw = data.get("usage", {})
                usage = {
                    "prompt_tokens": usage_raw.get("prompt_tokens", 0),
                    "completion_tokens": usage_raw.get("completion_tokens", 0),
                    "total_tokens": usage_raw.get("total_tokens", 0),
                    "duration": duration,
                    "tps": usage_raw.get("completion_tokens", 0) / duration if duration > 0 else 0
                }
                
                logger.info(f"[OpenAICompatible] OK | Prompt: {usage['prompt_tokens']} | Completion: {usage['completion_tokens']} | Time: {duration:.2f}s")
                return content, usage
                
            except requests.exceptions.RequestException as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(2 * (2 ** attempt))
        
        raise ConnectionError(f"OpenAICompatible no disponible: {last_error}")
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """Lista modelos disponibles en el endpoint."""
        return await asyncio.to_thread(self._list_models_sync)

    def _list_models_sync(self) -> List[Dict[str, Any]]:
        try:
            url = f"{self.base_url}/models"
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            session = self.get_session()
            response = session.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            models = []
            for m in data.get("data", []):
                models.append({
                    "id": m.get("id", ""),
                    "context_length": 128000,
                    "owned_by": "openai-compatible"
                })
            return models
        except Exception as e:
            logger.warning(f"[OpenAICompatible] Error listando modelos: {e}")
            return []
    
    async def sync_model_context(self):
        pass

    async def get_context_info(self) -> Dict[str, Any]:
        return {"max": self.context_max, "usable": self.usable}

    async def check_connection(self) -> bool:
        """Verifica conexión con el endpoint."""
        return await asyncio.to_thread(self._check_connection_sync)

    def _check_connection_sync(self) -> bool:
        try:
            url = f"{self.base_url}/models"
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            session = self.get_session()
            response = session.get(url, headers=headers, timeout=5)
            return response.status_code == 200
        except:
            return False

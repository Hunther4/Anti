"""
Anthropic Provider - Adapter para Anthropic Claude API (api.anthropic.com)

Requiere API key: export ANTHROPIC_API_KEY=sk-ant-...
"""

import requests
import os
import logging
import asyncio
import time
from typing import List, Dict, Tuple, Any

from .base import BaseProvider

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseProvider):
    """Proveedor para Anthropic Claude API."""
    
    DEFAULT_URL = "https://api.anthropic.com/v1"
    DEFAULT_MODEL = "claude-3-5-sonnet-20241022"
    
    def __init__(self, base_url: str = None, model: str = None, timeout: int = 180, api_key: str = None):
        super().__init__(
            base_url=base_url or self.DEFAULT_URL, 
            model=model or self.DEFAULT_MODEL,
            timeout=timeout
        )
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        
        if not self.api_key:
            logger.warning("[Anthropic] API key no configurada")
    
    async def chat(self, messages: List[Dict], temperature: float = 0.7) -> Tuple[str, Dict[str, Any]]:
        """Envía un chat a Anthropic."""
        return await asyncio.to_thread(self._chat_sync, messages, temperature)

    def _chat_sync(self, messages: List[Dict], temperature: float = 0.7) -> Tuple[str, Dict[str, Any]]:
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY no configurada")
            
        start_time = time.time()
        url = f"{self.base_url}/messages"
        
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        
        # Separar el system prompt para pasarlo a nivel superior según el estándar de Anthropic
        system_prompts = [msg["content"] for msg in messages if msg["role"] == "system"]
        system_text = "\n".join(system_prompts) if system_prompts else ""
        
        chat_messages = [
            {"role": msg["role"], "content": msg["content"]} 
            for msg in messages if msg["role"] in ["user", "assistant"]
        ]
        
        payload = {
            "model": self.model,
            "messages": chat_messages,
            "temperature": temperature,
            "max_tokens": 4000
        }
        if system_text:
            payload["system"] = system_text
            
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
                content = data['content'][0]['text']
                duration = time.time() - start_time
                
                usage_raw = data.get("usage", {})
                usage = {
                    "prompt_tokens": usage_raw.get("input_tokens", 0),
                    "completion_tokens": usage_raw.get("output_tokens", 0),
                    "total_tokens": usage_raw.get("input_tokens", 0) + usage_raw.get("output_tokens", 0),
                    "duration": duration,
                    "tps": usage_raw.get("output_tokens", 0) / duration if duration > 0 else 0
                }
                
                logger.info(f"[Anthropic] OK | Prompt: {usage['prompt_tokens']} | Completion: {usage['completion_tokens']} | Time: {duration:.2f}s")
                return content, usage
                
            except requests.exceptions.RequestException as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(2 * (2 ** attempt))
        
        raise ConnectionError(f"Anthropic no disponible: {last_error}")
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """Lista modelos Claude conocidos."""
        return [
            {"id": "claude-3-5-sonnet-20241022", "context_length": 200000, "owned_by": "anthropic"},
            {"id": "claude-3-5-haiku-20241022", "context_length": 200000, "owned_by": "anthropic"},
            {"id": "claude-3-opus-20240229", "context_length": 200000, "owned_by": "anthropic"}
        ]
    
    async def sync_model_context(self):
        pass

    async def get_context_info(self) -> Dict[str, Any]:
        return {"max": 200000, "usable": 180000}

    async def check_connection(self) -> bool:
        """Verifica la API key haciendo una llamada mínima."""
        return await asyncio.to_thread(self._check_connection_sync)

    def _check_connection_sync(self) -> bool:
        if not self.api_key:
            return False
        try:
            url = f"{self.base_url}/messages"
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            }
            # Cargar un prompt de saludo mínimo
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 5
            }
            session = self.get_session()
            response = session.post(url, json=payload, headers=headers, timeout=5)
            return response.status_code == 200
        except:
            return False

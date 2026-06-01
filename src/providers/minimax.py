"""
Minimax Provider - Adapter para Minimax API (api.minimax.chat)

Requiere API key: export MINIMAX_API_KEY=mm-...
"""

import httpx
import os
import logging
import asyncio
import time
from typing import List, Dict, Tuple, Any

from .base import BaseProvider

logger = logging.getLogger(__name__)


class MinimaxProvider(BaseProvider):
    """Proveedor para Minimax API."""
    
    DEFAULT_URL = "https://api.minimax.chat/v1"
    DEFAULT_MODEL = "abab6.5g-chat"
    
    def __init__(self, base_url: str = None, model: str = None, timeout: int = 180, api_key: str = None):
        super().__init__(
            base_url=base_url or self.DEFAULT_URL, 
            model=model or self.DEFAULT_MODEL,
            timeout=timeout
        )
        self.api_key = api_key or os.environ.get("MINIMAX_API_KEY", "")
        
        if not self.api_key:
            logger.warning("[Minimax] API key no configurada")
    
    async def chat(self, messages: List[Dict], temperature: float = 0.7) -> Tuple[str, Dict[str, Any]]:
        """Envía un chat a Minimax."""
        if not self.api_key:
            raise ValueError("MINIMAX_API_KEY no configurada")
            
        start_time = time.time()
        url = f"{self.base_url}/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": False
        }
        
        last_error = None
        for attempt in range(self.max_retries):
            try:
                session = await self.get_session()
                response = await session.post(
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
                
                logger.info(f"[Minimax] OK | Prompt: {usage['prompt_tokens']} | Completion: {usage['completion_tokens']} | Time: {duration:.2f}s")
                return content, usage
                
            except httpx.HTTPError as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 * (2 ** attempt))
        
        raise ConnectionError(f"Minimax no disponible: {last_error}")
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """Lista modelos Minimax."""
        return [
            {"id": "abab6.5g-chat", "context_length": 128000, "owned_by": "minimax"},
            {"id": "abab6.5s-chat", "context_length": 128000, "owned_by": "minimax"},
            {"id": "abab7-chat", "context_length": 128000, "owned_by": "minimax"}
        ]
    
    async def sync_model_context(self):
        pass
    
    async def get_context_info(self) -> Dict[str, Any]:
        return {"max": 128000, "usable": 120000}
    
    async def check_connection(self) -> bool:
        """Verifica la API key haciendo una llamada mínima."""
        if not self.api_key:
            return False
        try:
            url = f"{self.base_url}/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 5
            }
            session = await self.get_session()
            response = await session.post(url, json=payload, headers=headers, timeout=5)
            return response.status_code == 200
        except:
            return False

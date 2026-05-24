"""
LM Studio Provider - Adapter para LM Studio (http://localhost:1234)

LM Studio es una interfaz local para modelos GGUF/GGML.
API: http://localhost:1234/v1/chat/completions
"""

import requests
import asyncio
import logging
from typing import List, Dict, Tuple, Any

from .base import BaseProvider

logger = logging.getLogger(__name__)


class LMStudioProvider(BaseProvider):
    """Proveedor para LM Studio (compatible OpenAI)."""
    
    DEFAULT_URL = "http://127.0.0.1:1234"
    API_ENDPOINT = "/v1"
    
    def __init__(self, base_url: str = None, model: str = None, timeout: int = 120):
        super().__init__(
            base_url=base_url or f"{self.DEFAULT_URL}/v1", 
            model=model or "local-model",
            timeout=timeout
        )
    
    async def chat(self, messages: List[Dict], temperature: float = 0.7) -> Tuple[str, Dict[str, Any]]:
        """Envía un chat a LM Studio."""
        return await asyncio.to_thread(self._chat_sync, messages, temperature)

    def _chat_sync(self, messages: List[Dict], temperature: float = 0.7) -> Tuple[str, Dict[str, Any]]:
        import time
        
        url = f"{self.base_url}/chat/completions"
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": False
        }
        
        start_time = time.time()
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                session = self.get_session()
                response = session.post(
                    url, 
                    json=payload, 
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                data = response.json()
                content = data['choices'][0]['message']['content']
                duration = time.time() - start_time
                
                # Usage desde la response
                usage_raw = data.get('usage', {})
                try:
                    prompt_tokens = max(int(usage_raw.get('prompt_tokens', 0)), 0)
                    completion_tokens = max(int(usage_raw.get('completion_tokens', 0)), 0)
                    total_tokens = max(int(usage_raw.get('total_tokens', 0)), 0)
                except (ValueError, TypeError):
                    # Fallback: regex count
                    prompt_tokens = self.count_tokens(str(messages))
                    completion_tokens = self.count_tokens(content)
                    total_tokens = prompt_tokens + completion_tokens
                
                usage = {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens,
                    "duration": duration,
                    "tps": completion_tokens / duration if duration > 0 else 0
                }
                
                logger.info(f"[LM Studio] Prompt: {prompt_tokens} | Completion: {completion_tokens} | Time: {duration:.2f}s | TPS: {usage['tps']:.2f}")
                
                return content, usage
                
            except requests.exceptions.RequestException as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    import time as t
                    t.sleep(2 * (2 ** attempt))
        
        return f"Error conectando con LM Studio: {last_error}", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "duration": 0, "tps": 0}
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """Lista modelos disponibles en LM Studio."""
        return await asyncio.to_thread(self._list_models_sync)

    def _list_models_sync(self) -> List[Dict[str, Any]]:
        try:
            url = f"{self.base_url}/models"
            session = self.get_session()
            response = session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            models = []
            
            for model_data in data.get("data", []):
                model_id = model_data.get("id", "")
                context_length = model_data.get("context_length", 32000)
                
                models.append({
                    "id": model_id,
                    "context_length": context_length or 32000,
                    "owned_by": model_data.get("owned_by", "local")
                })
            
            return models
            
        except Exception as e:
            logger.warning(f"[LM Studio] Error listando modelos: {e}")
            return [{"id": self.model, "context_length": 32000}]
    
    async def sync_model_context(self):
        """Sincroniza modelo y contexto."""
        models = await self.list_models()
        if models:
            self.model = models[0]["id"]
            self.context_max = models[0]["context_length"]
            self.usable = self.context_max - 2000 # Reserva básica
            self.threshold = int(self.usable * 0.8)

    async def get_context_info(self) -> Dict[str, Any]:
        """Retorna info del contexto."""
        return {
            "max": self.context_max,
            "usable": self.usable,
            "threshold": self.threshold
        }

    async def check_connection(self) -> bool:
        """Verifica conexión con LM Studio."""
        return await asyncio.to_thread(self._check_connection_sync)

    def _check_connection_sync(self) -> bool:
        try:
            session = self.get_session()
            response = session.get(
                f"{self.base_url}/models",
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
    
    def count_tokens(self, text: str) -> int:
        """Cuenta tokens usando regex (aproximación)."""
        import re
        if not text:
            return 0
        words = re.findall(r"\b[\w']+\b", text)
        punct = re.findall(r"[^\w\s]", text)
        return len(words) + len(punct)
    
    def _get_context_length(self, model_id: str = None) -> int:
        """Obtiene el context_length del modelo."""
        model_id = model_id or self.model
        
        models = self.list_models()
        for m in models:
            if m.get("id") == model_id:
                return m.get("context_length", 32000)
        
        return 32000  # Default
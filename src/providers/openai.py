"""
OpenAI Provider - Adapter para OpenAI API (cloud.openai.com)

Requiere API key: export OPENAI_API_KEY=sk-...

API: https://api.openai.com/v1/chat/completions
"""

import requests
import os
import logging
from typing import List, Dict, Tuple, Any

from .base import BaseProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseProvider):
    """Proveedor para OpenAI API."""
    
    DEFAULT_URL = "https://api.openai.com/v1"
    DEFAULT_MODEL = "gpt-4o"
    
    def __init__(self, base_url: str = None, model: str = None, timeout: int = 180):
        super().__init__(
            base_url=base_url or self.DEFAULT_URL, 
            model=model or self.DEFAULT_MODEL,
            timeout=timeout
        )
        self.api_key = os.environ.get("OPENAI_API_KEY", "")
        
        if not self.api_key:
            logger.warning("[OpenAI] OPENAI_API_KEY no configurada")
    
    def chat(self, messages: List[Dict], temperature: float = 0.7) -> Tuple[str, Dict[str, Any]]:
        """Envía un chat a OpenAI."""
        import time
        
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY no configurada")
        
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
        
        start_time = time.time()
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
                
                logger.info(f"[OpenAI] Prompt: {usage['prompt_tokens']} | Completion: {usage['completion_tokens']} | Time: {duration:.2f}s")
                
                return content, usage
                
            except requests.exceptions.RequestException as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    import time as t
                    t.sleep(2 * (2 ** attempt))
        
        raise ConnectionError(f"OpenAI no disponible: {last_error}")
    
    def list_models(self) -> List[Dict[str, Any]]:
        """Lista modelos disponibles en OpenAI."""
        if not self.api_key:
            return []
        
        try:
            url = f"{self.base_url}/models"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            
            session = self.get_session()
            response = session.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            models = []
            
            # Filtrar solo chat models
            for model in data.get("data", []):
                model_id = model.get("id", "")
                if "gpt" in model_id.lower() or "chatgpt" in model_id.lower():
                    # OpenAI retorna context length en metadata
                    meta = model.get("metadata", {})
                    context_length = meta.get("context_window_tokens", 128000)
                    
                    models.append({
                        "id": model_id,
                        "context_length": context_length,
                        "owned_by": model.get("owned_by", "openai")
                    })
            
            return models
            
        except Exception as e:
            logger.warning(f"[OpenAI] Error listando modelos: {e}")
            return []
    
    def check_connection(self) -> bool:
        """Verifica conexión con OpenAI."""
        if not self.api_key:
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            session = self.get_session()
            response = session.get(
                f"{self.base_url}/models",
                headers=headers,
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
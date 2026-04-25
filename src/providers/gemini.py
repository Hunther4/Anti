"""
Google Gemini Provider - Adapter para Gemini API (generativelanguage.googleapis.com)

Requiere API key: export GEMINI_API_KEY=AI...

API: https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent
"""

import requests
import os
import json
import logging
from typing import List, Dict, Tuple, Any

from .base import BaseProvider

logger = logging.getLogger(__name__)


class GeminiProvider(BaseProvider):
    """Proveedor para Google Gemini."""
    
    DEFAULT_URL = "https://generativelanguage.googleapis.com/v1beta"
    DEFAULT_MODEL = "gemini-1.5-pro"
    
    # Model context lengths conocidos
    MODEL_CONTEXTS = {
        "gemini-1.5-pro": 128000,
        "gemini-1.5-flash": 128000,
        "gemini-1.0-pro": 32768,
        "gemini-pro": 32768,
    }
    
    def __init__(self, base_url: str = None, model: str = None, timeout: int = 180):
        super().__init__(
            base_url=base_url or self.DEFAULT_URL, 
            model=model or self.DEFAULT_MODEL,
            timeout=timeout
        )
        self.api_key = os.environ.get("GEMINI_API_KEY", "")
        
        if not self.api_key:
            logger.warning("[Gemini] GEMINI_API_KEY no configurada")
    
    def chat(self, messages: List[Dict], temperature: float = 0.7) -> Tuple[str, Dict[str, Any]]:
        """Envía un chat a Gemini."""
        import time
        
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY no configurada")
        
        # Gemini usa generateContent, no chat/completions
        url = f"{self.base_url}/models/{self.model}:generateContent"
        
        # Convertir mensajes al formato de Gemini
        contents = self._format_messages(messages)
        
        params = {"key": self.api_key}
        
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": 8192,
                "topP": 0.95,
                "topK": 40
            }
        }
        
        start_time = time.time()
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                session = self.get_session()
                response = session.post(
                    url, 
                    json=payload, 
                    params=params,
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                data = response.json()
                duration = time.time() - start_time
                
                # Extraer contenido
                candidate = data.get("candidates", [{}])[0]
                content = candidate.get("content", {})
                parts = content.get("parts", [])
                
                if parts:
                    content_text = parts[0].get("text", "")
                else:
                    content_text = ""
                
                # Usage (Gemini no da exactos, usar aproximación)
                prompt_tokens = self._estimate_tokens(str(messages))
                completion_tokens = self._estimate_tokens(content_text)
                
                usage = {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens,
                    "duration": duration,
                    "tps": completion_tokens / duration if duration > 0 else 0
                }
                
                logger.info(f"[Gemini] Prompt: {prompt_tokens} | Completion: {completion_tokens} | Time: {duration:.2f}s")
                
                return content_text, usage
                
            except requests.exceptions.RequestException as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    import time as t
                    t.sleep(2 * (2 ** attempt))
        
        raise ConnectionError(f" Gemini no disponible: {last_error}")
    
    def list_models(self) -> List[Dict[str, Any]]:
        """Lista modelos disponibles en Gemini."""
        if not self.api_key:
            return []
        
        try:
            url = f"{self.base_url}/models"
            params = {"key": self.api_key}
            
            session = self.get_session()
            response = session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            models = []
            
            for model in data.get("models", []):
                model_id = model.get("name", "").split("/")[-1]
                
                #获取 context length
                input_token_limit = model.get("inputTokenLimit", 32768)
                
                models.append({
                    "id": model_id,
                    "context_length": input_token_limit,
                    "display_name": model.get("displayName", model_id)
                })
            
            return models
            
        except Exception as e:
            logger.warning(f"[Gemini] Error listando modelos: {e}")
            return []
    
    def check_connection(self) -> bool:
        """Verifica conexión con Gemini."""
        if not self.api_key:
            return False
        
        try:
            # Intentar listar modelos
            url = f"{self.base_url}/models"
            params = {"key": self.api_key}
            
            session = self.get_session()
            response = session.get(url, params=params, timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def _format_messages(self, messages: List[Dict]) -> List[Dict]:
        """Convierte mensajes al formato de Gemini."""
        contents = []
        
        # Buscar system instruction
        system_content = None
        filtered_messages = []
        
        for msg in messages:
            if msg.get("role") == "system":
                system_content = msg.get("content", "")
            else:
                filtered_messages.append(msg)
        
        # Convertir a formato Gemini
        for msg in filtered_messages:
            role = "model" if msg.get("role") == "assistant" else msg.get("role", "user")
            
            contents.append({
                "role": role,
                "parts": [{"text": msg.get("content", "")}]
            })
        
        return contents
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimación aproximada de tokens."""
        # Aproximación: ~4 caracteres por token
        return len(text) // 4
    
    def _get_context_length(self, model_id: str = None) -> int:
        """Obtiene el context_length del modelo."""
        model_id = model_id or self.model
        
        return self.MODEL_CONTEXTS.get(model_id, 128000)
"""
Ollama Provider - Adapter para Ollama (http://localhost:11434)

Ollama es un LLM local que corre modelos como llama3, mistral, etc.
API: http://localhost:11434/api/chat
"""

import requests
import asyncio
import logging
from typing import List, Dict, Tuple, Any

from .base import BaseProvider

logger = logging.getLogger(__name__)


class OllamaProvider(BaseProvider):
    """Proveedor para Ollama."""
    
    DEFAULT_URL = "http://127.0.0.1:11434"
    API_ENDPOINT = "/api/chat"
    
    def __init__(self, base_url: str = None, model: str = None, timeout: int = 180):
        super().__init__(
            base_url=base_url or self.DEFAULT_URL, 
            model=model or "llama3",
            timeout=timeout
        )
        # Ollama usa el nombre del modelo tal cual
        self._model = model or "llama3"
    
    def chat(self, messages: List[Dict], temperature: float = 0.7) -> Tuple[str, Dict[str, Any]]:
        """Envia un chat a Ollama."""
        import time
        
        url = f"{self.base_url}{self.API_ENDPOINT}"
        
        # Convertir mensajes al formato de Ollama
        ollama_messages = self._format_messages(messages)
        
        payload = {
            "model": self._model,
            "messages": ollama_messages,
            "temperature": temperature,
            "stream": False,
            "options": {
                "temperature": temperature,
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
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                data = response.json()
                duration = time.time() - start_time
                
                # Extraer contenido
                content = data.get("message", {}).get("content", "")
                
                # Calcular usage (Ollama no retorna tokens directamente)
                # Usamos estimación aproximada
                prompt_tokens = sum(len(m.get("content", "")) // 4 for m in messages)
                completion_tokens = len(content) // 4
                total_tokens = prompt_tokens + completion_tokens
                
                usage = {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens,
                    "duration": duration,
                    "tps": completion_tokens / duration if duration > 0 else 0
                }
                
                logger.info(f"[Ollama] Prompt: {prompt_tokens} | Completion: {completion_tokens} | Time: {duration:.2f}s | TPS: {usage['tps']:.2f}")
                
                return content, usage
                
            except requests.exceptions.RequestException as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    import time as t
                    t.sleep(2 * (2 ** attempt))
        
        raise ConnectionError(f"Ollama no disponible después de {self.max_retries} intentos: {last_error}")
    
    def list_models(self) -> List[Dict[str, Any]]:
        """Lista modelos disponibles en Ollama."""
        try:
            url = f"{self.base_url}/api/tags"
            session = self.get_session()
            response = session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            models = []
            
            for model in data.get("models", []):
                model_name = model.get("name", "")
                # Parsear nombre y tamaño
                name_parts = model_name.split(":")
                model_id = name_parts[0] if name_parts else model_name
                
                # Ollama no da context_length directamente
                # Asumimos 8192 por defecto (la mayoria de modelos)
                context_length = 8192
                
                # Intentar detectar de tamaño del modelo
                size = model.get("size", 0)
                if size > 0:
                    # Modelos > 4GB probablemente tienen 32k
                    if size > 4 * 1024 * 1024 * 1024:
                        context_length = 32768
                    # Modelos > 8GB probablemente tienen 128k
                    elif size > 8 * 1024 * 1024 * 1024:
                        context_length = 131072
                
                models.append({
                    "id": model_id,
                    "name": model_name,
                    "context_length": context_length,
                    "size": size
                })
            
            # Si no hay modelos, usar default
            if not models:
                models.append({
                    "id": self._model,
                    "name": self._model,
                    "context_length": 8192,
                    "size": 0
                })
            
            return models
            
        except Exception as e:
            logger.warning(f"[Ollama] Error listando modelos: {e}")
            return [{"id": self._model, "context_length": 8192}]
    
    def check_connection(self) -> bool:
        """Verifica conexión con Ollama."""
        try:
            session = self.get_session()
            response = session.get(
                f"{self.base_url}/api/tags",
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
    
    def _format_messages(self, messages: List[Dict]) -> List[Dict]:
        """Convierte mensajes al formato de Ollama."""
        ollama_msgs = []
        
        for msg in messages:
            if msg.get("role") == "system":
                # Ollama no tiene systemMessages, agregar al inicio como user
                continue
            
            ollama_msgs.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })
        
        return ollama_msgs
    
    def _get_context_length(self, model_id: str = None) -> int:
        """Obtiene el context_length del modelo."""
        model_id = model_id or self._model
        
        # Intentar de las美国的 models
        models = self.list_models()
        for m in models:
            if m.get("id") == model_id or m.get("name", "").startswith(model_id):
                return m.get("context_length", 8192)
        
        return 8192  # Default
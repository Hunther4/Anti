"""
Ollama Provider - Adapter para Ollama (http://localhost:11434)

Ollama es un LLM local que corre modelos como llama3, mistral, etc.
API: http://localhost:11434/api/chat
"""

import httpx
import asyncio
import time
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
            base_url=base_url if base_url is not None else self.DEFAULT_URL,
            model=model or "llama3",
            timeout=timeout
        )

    async def chat(self, messages: List[Dict], temperature: float = 0.7) -> Tuple[str, Dict[str, Any]]:
        """Envia un chat a Ollama."""
        url = f"{self.base_url}{self.API_ENDPOINT}"

        ollama_messages = self._format_messages(messages)

        payload = {
            "model": self.model,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "temperature": temperature,
            }
        }

        start_time = time.time()
        last_error = None

        for attempt in range(self.max_retries):
            try:
                session = await self.get_session()
                response = await session.post(
                    url,
                    json=payload,
                    timeout=self.timeout
                )
                response.raise_for_status()

                data = response.json()
                duration = time.time() - start_time

                content = data.get("message", {}).get("content", "")

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

            except (httpx.HTTPError, ValueError, KeyError, IndexError) as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 * (2 ** attempt))

        raise ConnectionError(f"Ollama no disponible después de {self.max_retries} intentos: {last_error}")

    async def list_models(self) -> List[Dict[str, Any]]:
        """Lista modelos disponibles en Ollama."""
        try:
            url = f"{self.base_url}/api/tags"
            session = await self.get_session()
            response = await session.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            models = []

            for model in data.get("models", []):
                model_name = model.get("name", "")
                name_parts = model_name.split(":")
                model_id = name_parts[0] if name_parts else model_name

                context_length = 8192

                size = model.get("size", 0)
                if size > 0:
                    if size > 8 * 1024 * 1024 * 1024:
                        context_length = 131072
                    elif size > 4 * 1024 * 1024 * 1024:
                        context_length = 32768

                models.append({
                    "id": model_id,
                    "name": model_name,
                    "context_length": context_length,
                    "size": size
                })

            if not models:
                models.append({
                    "id": self.model,
                    "name": self.model,
                    "context_length": 8192,
                    "size": 0
                })

            return models

        except Exception as e:
            logger.warning(f"[Ollama] Error listando modelos: {e}")
            return [{"id": self.model, "context_length": 8192}]

    async def check_connection(self) -> bool:
        """Verifica conexión con Ollama."""
        try:
            session = await self.get_session()
            response = await session.get(
                f"{self.base_url}/api/tags",
                timeout=5
            )
            return response.status_code == 200
        except Exception:
            return False

    def _format_messages(self, messages: List[Dict]) -> List[Dict]:
        """Convierte mensajes al formato de Ollama."""
        ollama_msgs = []

        for msg in messages:
            ollama_msgs.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })

        return ollama_msgs

    async def sync_model_context(self):
        """Sincroniza modelo y contexto."""
        models = await self.list_models()
        if models:
            self.model = models[0]["id"]
            self.context_max = models[0]["context_length"]
            self.usable = self.context_max - 2000
            self.threshold = int(self.usable * 0.8)

    async def get_context_info(self) -> Dict[str, Any]:
        """Retorna info del contexto."""
        return {
            "max": self.context_max,
            "usable": self.usable,
            "threshold": self.threshold
        }

    async def _get_context_length(self, model_id: str = None) -> int:
        """Obtiene el context_length del modelo."""
        model_id = model_id or self.model

        models = await self.list_models()
        for m in models:
            if m.get("id") == model_id or m.get("name", "").startswith(model_id):
                return m.get("context_length", 8192)

        return 8192

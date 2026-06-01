"""
Base Provider - Interfaz abstracta para todos los proveedores de LLM.

Cada proveedor debe implementar esta interfaz:
- chat(messages, temperature) -> (content, usage)
- list_models() -> [models]
- sync_model_context() -> None
- check_connection() -> bool
"""

import threading
import httpx
from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Any, Optional


class BaseProvider(ABC):
    """Interfaz abstracta para proveedores de LLM."""
    
    def __init__(self, base_url: str, model: str = None, timeout: int = 120):
        self.base_url = base_url.rstrip("/")
        self.model = model or "local-model"
        self.timeout = timeout
        self._session = None
        self.max_retries = 3
        self.context_max = 32000
        self.usable = 32000
        self.threshold = 16000
        self.tps_history = []
    
    def record_usage(self, usage: dict):
        """Registra la telemetría de TPS del chat actual."""
        tps = usage.get("tps", 0.0)
        if tps > 0:
            self.tps_history.append(tps)
            if len(self.tps_history) > 50:
                self.tps_history.pop(0)
    
    @abstractmethod
    async def chat(self, messages: List[Dict], temperature: float = 0.7) -> Tuple[str, Dict[str, Any]]:
        """Envía un mensaje al LLM y retorna la respuesta."""
        pass
    
    @abstractmethod
    async def list_models(self) -> List[Dict[str, Any]]:
        """Lista los modelos disponibles."""
        pass

    @abstractmethod
    async def sync_model_context(self):
        """Sincroniza el nombre y contexto del modelo."""
        pass
    
    @abstractmethod
    async def get_context_info(self) -> Dict[str, Any]:
        """Retorna información detallada sobre el contexto."""
        pass

    async def get_model_info(self) -> str:
        """Retorna el nombre del modelo actual."""
        return self.model
    
    @abstractmethod
    async def check_connection(self) -> bool:
        """Verifica conexión con el proveedor."""
        pass
    
    async def get_session(self) -> httpx.AsyncClient:
        """Obtiene o crea una sesión HTTP asíncrona reusable."""
        if self._session is None:
            self._session = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout, connect=10),
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
            )
        return self._session
    
    async def close(self):
        """Cierra la sesión HTTP si existe."""
        if self._session:
            await self._session.aclose()
            self._session = None
    
    def __del__(self):
        self.close()
    
    # --- Utilidades comunes ---
    
    def _format_messages(self, messages: List[Dict]) -> List[Dict]:
        return messages

class ProviderFactory:
    """Factory para crear proveedores automáticamente."""
    
    _lock = threading.Lock()
    PROVIDERS = {
        "lmstudio": None,  # Se importa lazy
        "ollama": None,
        "openai": None,
        "gemini": None,
        "deepseek": None,
        "openaicompatible": None,
        "anthropic": None,
        "minimax": None,
    }
    
    @classmethod
    async def detect(cls, base_url: str = None) -> Optional[str]:
        """
        Detecta el proveedor conectado de forma asíncrona.
        """
        async with httpx.AsyncClient(timeout=2) as client:
            if base_url:
                try:
                    r = await client.get(base_url)
                    if r.status_code < 500:
                        return base_url
                except Exception:
                    pass
            else:
                for port in [1234, 11434, 8000, 8001]:
                    try:
                        endpoint = "/api/tags" if port == 11434 else "/v1/models"
                        url = f"http://127.0.0.1:{port}"
                        r = await client.get(f"{url}{endpoint}")
                        if r.status_code == 200:
                            return url if port == 11434 else f"{url}/v1"
                    except Exception:
                        continue
        
        return None
    
    @classmethod
    def create(cls, provider: str, **kwargs):
        """Crea un proveedor específico."""
        with cls._lock:
            if cls.PROVIDERS.get(provider) is None:
                # Load lazy
                if provider == "lmstudio":
                    from .lmstudio import LMStudioProvider
                    cls.PROVIDERS[provider] = LMStudioProvider
                elif provider == "ollama":
                    from .ollama import OllamaProvider
                    cls.PROVIDERS[provider] = OllamaProvider
                elif provider == "openai":
                    from .openai import OpenAIProvider
                    cls.PROVIDERS[provider] = OpenAIProvider
                elif provider == "gemini":
                    from .gemini import GeminiProvider
                    cls.PROVIDERS[provider] = GeminiProvider
                elif provider == "deepseek":
                    from .deepseek import DeepSeekProvider
                    cls.PROVIDERS[provider] = DeepSeekProvider
                elif provider == "openaicompatible":
                    from .openaicompatible import OpenAICompatibleProvider
                    cls.PROVIDERS[provider] = OpenAICompatibleProvider
                elif provider == "anthropic":
                    from .anthropic import AnthropicProvider
                    cls.PROVIDERS[provider] = AnthropicProvider
                elif provider == "minimax":
                    from .minimax import MinimaxProvider
                    cls.PROVIDERS[provider] = MinimaxProvider
                else:
                    raise ValueError(f"Proveedor desconocido: {provider}")
        
        provider_class = cls.PROVIDERS.get(provider)
        if provider_class:
            return provider_class(**kwargs)
        
        raise ValueError(f"Proveedor desconocido: {provider}")
    
    @classmethod
    async def auto_create(cls, base_url: str = None, **kwargs):
        """
        Auto-detecta y crea el proveedor.
        """
        detected = await cls.detect(base_url)
        
        if detected:
            if ":11434" in detected:
                return cls.create("ollama", base_url=detected, **kwargs)
            elif ":1234" in detected or "/v1" in detected:
                return cls.create("lmstudio", base_url=detected, **kwargs)
        
        return cls.create("lmstudio", base_url=base_url if base_url is not None else "http://127.0.0.1:1234/v1", **kwargs)
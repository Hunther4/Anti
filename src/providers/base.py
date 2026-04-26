"""
Base Provider - Interfaz abstracta para todos los proveedores de LLM.

Cada proveedor debe implementar esta interfaz:
- chat(messages, temperature) -> (content, usage)
- list_models() -> [models]
- sync_model_context() -> None
- check_connection() -> bool
"""

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
    
    def get_session(self):
        """Obtiene o crea una sesión HTTP reusable."""
        if self._session is None:
            import requests
            from requests.adapters import HTTPAdapter
            
            self._session = requests.Session()
            adapter = HTTPAdapter(
                pool_connections=10, 
                pool_maxsize=10, 
                max_retries=0
            )
            self._session.mount('http://', adapter)
            self._session.mount('https://', adapter)
        return self._session
    
    # --- Utilidades comunes ---
    
    def _format_messages(self, messages: List[Dict]) -> List[Dict]:
        """Formatea mensajes para el proveedor específico."""
        return messages
    
    def _parse_usage(self, response_data: Dict, duration: float) -> Dict[str, Any]:
        """ parse usage desde la respuesta del proveedor."""
        usage = response_data.get("usage", {})
        return {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "duration": duration,
            "tps": usage.get("completion_tokens", 0) / duration if duration > 0 else 0
        }


class ProviderFactory:
    """Factory para crear proveedores automáticamente."""
    
    PROVIDERS = {
        "lmstudio": None,  # Se importa lazy
        "ollama": None,
        "openai": None,
        "gemini": None,
    }
    
    @classmethod
    def detect(cls, base_url: str = None) -> str:
        """
        Detecta el proveedor conectado.
        """
        import requests
        
        if base_url:
            url = base_url
        else:
            for port in [1234, 11434, 8000, 8001]:
                try:
                    r = requests.get(f"http://127.0.0.1:{port}/v1/models", timeout=2)
                    if r.status_code == 200:
                        return f"http://127.0.0.1:{port}/v1"
                except:
                    continue
        
        return None
    
    @classmethod
    def create(cls, provider: str, **kwargs):
        """Crea un proveedor específico."""
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
            else:
                raise ValueError(f"Proveedor desconocido: {provider}")
        
        provider_class = cls.PROVIDERS.get(provider)
        if provider_class:
            return provider_class(**kwargs)
        
        raise ValueError(f"Proveedor desconocido: {provider}")
    
    @classmethod
    def auto_create(cls, base_url: str = None, **kwargs):
        """
        Auto-detecta y crea el proveedor.
        """
        detected = cls.detect(base_url)
        
        if detected:
            if ":1234" in detected or "/v1" in detected:
                return cls.create("lmstudio", base_url=detected, **kwargs)
            elif ":11434" in detected:
                return cls.create("ollama", base_url=detected, **kwargs)
        
        return cls.create("lmstudio", base_url=base_url or "http://127.0.0.1:1234/v1", **kwargs)
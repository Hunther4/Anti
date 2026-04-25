"""
Providers - Módulo para múltiples proveedores de LLM.

Proveedores disponibles:
- LM Studio (local, OpenAI-compatible)
- Ollama (local)
- OpenAI (cloud)
- Gemini (cloud)

Uso:
    from src.providers import auto_create
    
    # Auto-detectar proveedor
    provider = auto_create()
    
    # O crear específico
    from src.providers import create_provider
    provider = create_provider("ollama", model="llama3")
"""

from .base import BaseProvider, ProviderFactory
from .lmstudio import LMStudioProvider
from .ollama import OllamaProvider


# Aliases convenientes
def auto_create(base_url: str = None, **kwargs):
    """Crea un proveedor auto-detectado."""
    return ProviderFactory.auto_create(base_url=base_url, **kwargs)


def create_provider(provider: str, **kwargs):
    """Crea un proveedor específico."""
    return ProviderFactory.create(provider, **kwargs)


__all__ = [
    "BaseProvider",
    "ProviderFactory", 
    "LMStudioProvider",
    "OllamaProvider",
    "auto_create",
    "create_provider",
]
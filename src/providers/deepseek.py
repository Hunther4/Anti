"""
DeepSeek Provider - Adapter para DeepSeek API
Compatible con OpenAI API
"""

import logging
from typing import List, Dict, Tuple, Any
from .openai import OpenAIProvider

logger = logging.getLogger(__name__)

class DeepSeekProvider(OpenAIProvider):
    """Proveedor para DeepSeek API."""
    
    DEFAULT_URL = "https://api.deepseek.com"
    DEFAULT_MODEL = "deepseek-chat"
    
    def __init__(self, base_url: str = None, model: str = None, timeout: int = 180, api_key: str = None):
        super().__init__(
            base_url=base_url or self.DEFAULT_URL, 
            model=model or self.DEFAULT_MODEL,
            timeout=timeout,
            api_key=api_key
        )
        if not self.api_key:
            logger.warning("[DeepSeek] API key no configurada")

    async def list_models(self) -> List[Dict[str, Any]]:
        """DeepSeek a veces tiene restricciones en list_models, retornamos los comunes."""
        return [
            {"id": "deepseek-chat", "context_length": 64000, "owned_by": "deepseek"},
            {"id": "deepseek-coder", "context_length": 64000, "owned_by": "deepseek"},
        ]

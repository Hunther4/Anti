import asyncio
import unittest
from unittest.mock import patch, MagicMock
import src.tools as tools
from src.providers.openai import OpenAIProvider
from src.providers.anthropic import AnthropicProvider
from src.providers.gemini import GeminiProvider
from src.providers.deepseek import DeepSeekProvider
from src.providers.ollama import OllamaProvider
from src.providers.lmstudio import LMStudioProvider
from src.providers.minimax import MinimaxProvider
from src.providers.openaicompatible import OpenAICompatibleProvider

class TestSprint1(unittest.IsolatedAsyncioTestCase):

    # --- Security Tests ---

    async def test_run_local_command_no_fallback(self):
        """Verify that run_local_command returns security error when docker is missing."""
        # Mock subprocess.run to simulate docker missing (command not found)
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError("docker: command not found")
            
            result = tools.run_local_command("ls -la")
            self.assertIn("[SEGURIDAD]", result)
            self.assertIn("Docker no está disponible", result)

    async def test_is_safe_url_private_ip(self):
        """Verify that is_safe_url blocks private IPs."""
        unsafe_urls = [
            "http://127.0.0.1",
            "http://localhost",
            "http://192.168.1.1",
            "http://10.0.0.1",
            "http://169.254.169.254",
        ]
        for url in unsafe_urls:
            self.assertFalse(tools.is_safe_url(url), f"URL {url} should be unsafe")

    async def test_fetch_url_text_security(self):
        """Verify fetch_url_text blocks unsafe URLs."""
        result = tools.fetch_url_text("http://127.0.0.1")
        self.assertIn("[SEGURIDAD]", result)

    async def test_browser_fetch_security(self):
        """Verify browser_fetch blocks unsafe URLs."""
        result = await tools.browser_fetch("http://127.0.0.1")
        self.assertIn("[SEGURIDAD]", result)

    # --- Provider Async/Import Tests ---

    async def test_providers_list_models(self):
        """Verify all providers can be instantiated and list_models called without errors."""
        providers = [
            OpenAIProvider(),
            AnthropicProvider(),
            GeminiProvider(),
            DeepSeekProvider(),
            OllamaProvider(),
            LMStudioProvider(),
            MinimaxProvider(),
            OpenAICompatibleProvider(),
        ]
        
        for provider in providers:
            try:
                # We don't care about the result (API keys might be missing), 
                # just that it doesn't crash with ImportError or asyncio errors.
                await provider.list_models()
            except Exception as e:
                # Ignore API key errors, but crash on type/import/async errors
                if "API key" in str(e) or "ConnectionError" in str(e) or "ValueError" in str(e):
                    continue
                self.fail(f"Provider {provider.__class__.__name__} crashed during list_models: {e}")

if __name__ == "__main__":
    unittest.main()

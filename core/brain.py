import requests
import asyncio

class Brain:
    def __init__(self, base_url="http://127.0.0.1:1234/v1"):
        self.base_url = base_url
        self.model = "local-model"

    async def chat(self, messages, temperature=0.7):
        return await asyncio.to_thread(self._chat_sync, messages, temperature)

    def _chat_sync(self, messages, temperature):
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature
        }
        try:
            # 15 minutes timeout as requested
            response = requests.post(url, json=payload, timeout=900)
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
        except Exception as e:
            return f"Error conectando con LM Studio: {e}"

    async def get_model_info(self):
        return await asyncio.to_thread(self._get_model_info_sync)

    def _get_model_info_sync(self):
        try:
            res = requests.get(f"{self.base_url}/models", timeout=5)
            data = res.json()
            if 'data' in data and len(data['data']) > 0:
                return data['data'][0]['id']
            return "Modelo Desconocido"
        except:
            return "Desconectado"

    async def check_connection(self):
        return await asyncio.to_thread(self._check_connection_sync)

    def _check_connection_sync(self):
        try:
            res = requests.get(f"{self.base_url}/models", timeout=5)
            return res.status_code == 200
        except:
            return False

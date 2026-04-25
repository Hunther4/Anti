import requests
import asyncio
import re
import logging

logger = logging.getLogger(__name__)


# --- MCP Tool Registry (v1.0) ---
# Tools available via MCP protocol
MCP_TOOLS = {
    "duckduckgo_search": {
        "description": "Search the web using DuckDuckGo or SearxNG",
        "category": "search",
    },
    "fetch_url_text": {
        "description": "Fetch and extract clean text content from a URL",
        "category": "fetch",
    },
    "write_file": {
        "description": "Write content to a file in the workspace",
        "category": "file",
    },
    "read_file": {
        "description": "Read content from a file in the workspace",
        "category": "file",
    },
    "run_local_command": {
        "description": "Execute a shell command locally",
        "category": "system",
    },
    "autonomous_research": {
        "description": "Search and automatically fetch top results in parallel",
        "category": "research",
    },
}


def is_mcp_tool(tool_name: str) -> bool:
    """
    Check if a tool name is registered as an MCP tool.
    Returns True if the tool should be invoked via MCP protocol.
    """
    if not tool_name:
        return False
    return tool_name in MCP_TOOLS


def get_tool_category(tool_name: str) -> str:
    """Get the category of a tool for routing decisions."""
    tool = MCP_TOOLS.get(tool_name, {})
    return tool.get("category", "unknown")


class Brain:
    def __init__(self, base_url="http://127.0.0.1:1234/v1"):
        self.base_url = base_url
        self.model = "local-model"
        self._session = None
        self.max_retries = 3
        self.timeout = 120
        
        # Context-aware config (v0.5)
        self.context_max = 32000
        self.reserved_system = 8000
        self.reserved_completion = 4000
        self.usable_threshold = 0.85
        self.usable = self.context_max - self.reserved_system - self.reserved_completion
        self.threshold = int(self.usable * self.usable_threshold)
        self.last_prompt_tokens = 0

    def _get_session(self):
        if self._session is None:
            self._session = requests.Session()
            adapter = requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=10, max_retries=0)
            self._session.mount('http://', adapter)
            self._session.mount('https://', adapter)
        return self._session

    async def chat(self, messages, temperature=0.7):
        return await asyncio.to_thread(self._chat_sync, messages, temperature)

    def _chat_sync(self, messages, temperature):
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": False
        }
        
        import json
        payload_size = len(json.dumps(payload))
        print(f"[*] Payload size: {payload_size} bytes")
        
        last_error = None
        for attempt in range(self.max_retries):
            try:
                import time
                start_time = time.time()
                session = self._get_session()
                response = session.post(url, json=payload, timeout=self.timeout)
                response.raise_for_status()
                end_time = time.time()
                
                data = response.json()
                content = data['choices'][0]['message']['content']
                
                # v1.4 Sentinel Fix: Robust usage parsing (Auto-Audit Recommendation)
                usage_raw = data.get('usage', {})
                try:
                    prompt_tokens = max(int(usage_raw.get('prompt_tokens', 0)), 0)
                    completion_tokens = max(int(usage_raw.get('completion_tokens', 0)), 0)
                    total_tokens = max(int(usage_raw.get('total_tokens', 0)), 0)
                except (ValueError, TypeError):
                    # Fallback to regex count if server data is corrupt
                    print("[!] Sentinel Warning: Data corruption in 'usage'. Using Regex Fallback.")
                    prompt_tokens = self.count_tokens(str(messages))
                    completion_tokens = self.count_tokens(content)
                    total_tokens = prompt_tokens + completion_tokens
                
                usage = {
                    'prompt_tokens': prompt_tokens,
                    'completion_tokens': completion_tokens,
                    'total_tokens': total_tokens,
                    'duration': end_time - start_time,
                    'tps': (completion_tokens / (end_time - start_time)) if (end_time - start_time) > 0 else 0
                }
                
                duration = end_time - start_time
                tps = completion_tokens / duration if duration > 0 else 0
                
                # Log metrics to console (optional but helpful for the user)
                print(f"\n[METRICS] Prompt: {prompt_tokens} | Completion: {completion_tokens} | Total: {total_tokens}")
                print(f"[METRICS] Time: {duration:.2f}s | Speed: {tps:.2f} t/s\n")
                
                # Update context info based on response (if model provides context info)
                # Note: 'usage' doesn't give context_length, but we store current prompt size
                self.last_prompt_tokens = prompt_tokens
                
                return content, usage
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(2 * (2 ** attempt))
                    
        return "Error conectando con LM Studio...", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "duration": 0, "tps": 0}

    async def get_context_info(self):
        """Retorna información detallada sobre el contexto del modelo (v0.4 CORREGIDO)."""
        try:
            res = await asyncio.to_thread(requests.get, f"{self.base_url}/models", timeout=5)
            data = res.json()
            if 'data' in data and len(data['data']) > 0:
                model_data = data['data'][0]
                # Algunos servidores como LM Studio o LocalAI reportan context_length
                self.context_max = model_data.get('context_length', self.context_max)
                self.model = model_data.get('id', self.model)
        except requests.RequestException as e:
            logger.warning(f"[Brain] Error fetching model info: {e}")
        except json.JSONDecodeError as e:
            logger.warning(f"[Brain] Invalid JSON from API: {e}")

        # v0.4 CORREGIDO: NUNCA negativo
        usable = self.context_max - self.reserved_system - self.reserved_completion
        usable = max(usable, 0)
        
        threshold = int(usable * self.usable_threshold)
        threshold = max(threshold, int(usable * 0.5))  # Mínimo 50%
        
        return {
            "max": self.context_max,
            "usable": self.usable,
            "threshold": self.threshold,
            "reserved_system": self.reserved_system,
            "reserved_completion": self.reserved_completion
        }


    async def check_connection(self):
        """Verifica conexión con el servidor (v0.6 Compatibility)."""
        return await asyncio.to_thread(self._check_connection_sync)

    def _check_connection_sync(self):
        try:
            res = requests.get(f"{self.base_url}/models", timeout=5)
            return res.status_code == 200
        except requests.RequestException as e:
            logger.warning(f"[Brain] Connection check failed: {e}")
            return False

    def _update_thresholds(self):
        """Recalcula los límites tras un cambio de contexto."""
        self.usable = max(self.context_max - self.reserved_system - self.reserved_completion, 0)
        self.threshold = int(self.usable * self.usable_threshold)
        self.threshold = max(self.threshold, int(self.usable * 0.5))

    # ==================== v0.4: Token Counting ====================
    
    def count_tokens(self, text: str) -> int:
        """Cuenta tokens de forma precisa usando regex."""
        if not text:
            return 0
        words = re.findall(r"\b[\w']+\b", text)
        punct = re.findall(r"[^\w\s]", text)
        return len(words) + len(punct)

    def count_tokens_estimate(self, text: str) -> int:
        """Estimación rápida - divide por 4."""
        return len(text) // 4

    # ==================== v0.4: Context-Aware Calculations ====================
    
    def calc_usable_context(self, context_length: int) -> int:
        """Calcula contexto usable SIN overflow (v0.4 CORREGIDO)."""
        if context_length < 8192:
            reserved_system = 500
            reserved_completion = 1000
        elif context_length < 32768:
            reserved_system = 1500
            reserved_completion = 3000
        else:
            reserved_system = 2000
            reserved_completion = 4000
        
        usable = context_length - reserved_system - reserved_completion
        return max(usable, 0)  # NUNCA negativo

    def calc_threshold(self, usable: int) -> int:
        """Threshold que NUNCA es negativo (v0.4)."""
        threshold = int(usable * 0.7)
        return max(threshold, int(usable * 0.5))  # Mínimo 50%

    # ==================== v0.4: U-Shape ====================
    
    def ushape_order(self, chunks: list) -> list:
        """
        U-shape ordering para máxima atención.
        [A, B, C, D, E] → [A, C, E, D, B]
        """
        if len(chunks) <= 3:
            return chunks
        
        result = []
        front = []
        back = []
        
        for i, chunk in enumerate(chunks):
            if i % 2 == 0:
                front.append(chunk)
            else:
                back.append(chunk)
        
        back.reverse()
        result.extend(front)
        result.extend(back)
        
        return result

    # ==================== v0.5: DYNAMIC CONTEXT SYNC ====================
    
    async def sync_model_context(self) -> dict:
        """
        Detecta el context_length real del modelo dinámicamente.
        Combina API + fallback + cache.
        """
        try:
            res = await asyncio.to_thread(requests.get, f"{self.base_url}/models", timeout=5)
            data = res.json()
            
            if 'data' in data and len(data['data']) > 0:
                model_data = data['data'][0]
                
                new_model = model_data.get('id', self.model)
                new_context = model_data.get('context_length', self.context_max)
                old_context = self.context_max
                
                changed = False
                if new_model != self.model:
                    print(f"[v0.5] Model changed: {self.model} → {new_model}")
                    self.model = new_model
                    changed = True
                
                if new_context != old_context:
                    print(f"[v0.5] Context changed: {old_context} → {new_context}")
                    self.context_max = new_context
                    self._update_threshold()
                    changed = True
                
                return {"changed": changed, "old_context": old_context, "new_context": self.context_max, "model": self.model}
                    
        except Exception as e:
            print(f"[v0.5] Context sync failed: {e}")
        
        return {"changed": False}
    
    def _update_threshold(self):
        """Recalcula threshold después de cambio de contexto."""
        usable = self.context_max - self.reserved_system - self.reserved_completion
        usable = max(usable, 0)
        
        self.usable = usable
        self.threshold = int(usable * 0.85)
        self.threshold = max(self.threshold, int(usable * 0.5))

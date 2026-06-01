import os
import sys
import threading
import secrets

# --- SECURITY EARLY-BOOT ---
SHARED_SECRET = b""

def _umbilical_cord():
    try:
        while True:
            chunk = sys.stdin.buffer.read(1024)
            if not chunk:
                break
    except Exception:
        pass
    print("[SECURITY] Parent process died or stdin closed. Emergency shutdown.", flush=True)
    os._exit(0)

def _init_security():
    global SHARED_SECRET
    if os.environ.get("ANTI_MANAGED") == "1":
        try:
            SHARED_SECRET = sys.stdin.buffer.read(32)
            if len(SHARED_SECRET) != 32:
                print("[SECURITY] Failed to read 32-byte secret. Exiting.", flush=True)
                os._exit(1)
            t = threading.Thread(target=_umbilical_cord, daemon=True)
            t.start()
        except Exception as e:
            print(f"[SECURITY] Boot error: {e}", flush=True)
            os._exit(1)
    else:
        SHARED_SECRET = secrets.token_bytes(32)

_init_security()
# ---------------------------

import json
import webbrowser
import uuid
import asyncio
import logging
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler, ThreadingHTTPServer

# Corrected imports for the current structure
from src.agent import AntiAgent
from src.tools import read_file

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

agent = None
agent_lock = threading.Lock()
active_jobs = {}
active_jobs_lock = threading.Lock()

# Load server port from config (Local-First: config.local.json > config.json)
def _load_port():
    for candidate in ("config.local.json", "config.json"):
        if os.path.exists(candidate):
            try:
                with open(candidate, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                return cfg.get("server_port", 8000)
            except Exception:
                logging.exception("Failed to load server config from %s", candidate)
                return 8000
    logging.error(
        "Configuration file not found. Please copy config.json.example to "
        "config.local.json and fill in your keys."
    )
    return 8000

SERVER_PORT = _load_port()

# Thread-safe persistent event loop for multithreaded asyncio execution
LOOP = asyncio.new_event_loop()

def start_event_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

loop_thread = threading.Thread(target=start_event_loop, args=(LOOP,), daemon=True)
loop_thread.start()

def run_async(coro):
    """Ejecuta corutinas de forma segura y bloqueante entre hilos usando el event loop persistente."""
    return asyncio.run_coroutine_threadsafe(coro, LOOP).result()


# MCP servers storage
MCP_FILE = os.path.join(BASE_DIR, "memory", "mcp_servers.json")

def load_mcps():
    if os.path.exists(MCP_FILE):
        try:
            with open(MCP_FILE, "r") as f:
                return json.load(f)
        except Exception:
            logging.exception("Failed to load MCP servers")
            return []
    return []

def save_mcps(mcps):
    os.makedirs(os.path.dirname(MCP_FILE), exist_ok=True)
    with open(MCP_FILE, "w") as f:
        json.dump(mcps, f, indent=2)


def background_agent_task(job_id, message, image_data):
    """Ejecuta el agente en segundo plano y guarda el resultado en active_jobs."""
    from src.logger import set_request_id
    import uuid as _uuid
    rid = _uuid.uuid4().hex[:12]
    set_request_id(rid)
    try:
        with agent_lock:
            response_obj = run_async(agent.handle_command(message, image_data=image_data))
        
        if response_obj is None:
            response_obj = {"response": "Comando ejecutado.", "steps": []}
        if isinstance(response_obj, str):
            response_obj = {"response": response_obj, "steps": []}
        response_obj["request_id"] = rid
            
        with active_jobs_lock:
            active_jobs[job_id]["status"] = "completed"
            active_jobs[job_id]["result"] = response_obj
            active_jobs[job_id]["_ts"] = time.time()
    except Exception as e:
        with active_jobs_lock:
            active_jobs[job_id]["status"] = "failed"
            active_jobs[job_id]["error"] = str(e)
            active_jobs[job_id]["_ts"] = time.time()


class APIHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Point to the web directory in extras/web
        web_dir = os.path.join(BASE_DIR, "extras", "web")
        super().__init__(*args, directory=web_dir, **kwargs)

    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def do_GET(self):
        path_base = self.path.split('?')[0]

        if path_base == '/api/refresh':
            agent.config = agent._load_config()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "refreshed"}).encode('utf-8'))
            return

        if path_base.startswith('/api/job/'):
            job_id = path_base.replace('/api/job/', '').split('/')[0]
            if '..' in job_id or '/' in job_id:
                self.send_error(400, "Invalid job_id")
                return
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            with active_jobs_lock:
                job = active_jobs.get(job_id, {"status": "not_found"})
                # Cleanup completed jobs older than 1 hour to prevent memory leak
                stale_ids = [
                    jid for jid, jdata in active_jobs.items()
                    if jdata.get("status") in ("completed", "failed")
                    and time.time() - jdata.get("_ts", time.time()) > 3600
                ]
                for stale_id in stale_ids:
                    del active_jobs[stale_id]
            try:
                self.wfile.write(json.dumps(job).encode('utf-8'))
            except Exception:
                logging.exception("Failed to send job response")
            return

        if path_base == '/api/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            # Hybrid Memory Stats
            archive_stats = run_async(agent.memory.archive.get_stats()) if hasattr(agent.memory, 'archive') else {"archived_engrams": 0}

            try:
                run_async(agent.brain.get_context_info())
                status = {
                    "connected": run_async(agent.brain.check_connection()),
                    "agent_name": agent.config.get("agent_name", "Anti"),
                    "loaded_model": agent.brain.model,
                    "files_count": agent.memory.count_workspace_files(),
                    "engrams_count": agent.memory.count_engrams(),
                    "archived_count": archive_stats.get("archived_engrams", 0),
                    "reasoner_mode": agent.reasoner_mode,
                }
                self.wfile.write(json.dumps(status).encode('utf-8'))
            except Exception as e:
                # Basic status if something fails
                basic_status = {
                    "connected": False,
                    "agent_name": agent.config.get("agent_name", "Anti"),
                    "loaded_model": "Error",
                    "files_count": agent.memory.count_workspace_files(),
                    "engrams_count": agent.memory.count_engrams(),
                    "archived_count": archive_stats.get("archived_engrams", 0),
                    "reasoner_mode": agent.reasoner_mode,
                    "error": str(e)
                }
                try:
                    self.wfile.write(json.dumps(basic_status).encode('utf-8'))
                except Exception:
                    logging.exception("Failed to send basic status")
            return

        elif path_base == '/api/telemetry':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            try:
                from src.tools import wigolo_cache
                tps_history = getattr(agent.brain, 'tps_history', [])
                avg_tps = sum(tps_history) / len(tps_history) if tps_history else 0.0
                
                cache_total = wigolo_cache.hits + wigolo_cache.misses
                cache_ratio = wigolo_cache.hits / cache_total if cache_total > 0 else 0.0
                
                telemetry = {
                    "average_tps": round(avg_tps, 2),
                    "cache_hits": wigolo_cache.hits,
                    "cache_misses": wigolo_cache.misses,
                    "cache_hit_ratio": round(cache_ratio, 2),
                    "context_max": getattr(agent.brain, 'context_max', 32000),
                    "context_usable": getattr(agent.brain, 'usable', 30000),
                    "context_threshold": getattr(agent.brain, 'threshold', 24000),
                    "engrams_count": agent.memory.count_engrams(),
                    "skills_count": len(agent.memory.skills.skills) if hasattr(agent.memory.skills, 'skills') else 0
                }
                self.wfile.write(json.dumps(telemetry).encode('utf-8'))
            except Exception as e:
                try:
                    self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
                except Exception:
                    logging.exception("Failed to send telemetry error")
            return

        elif path_base == '/api/knowledge_graph':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            try:
                import sqlite3
                db_path = agent.memory.archive.db_path
                with sqlite3.connect(db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    
                    # Fetch entities
                    cursor.execute("SELECT id, observation_id, entity_type, value, timestamp FROM entities ORDER BY id DESC LIMIT 500")
                    entities = [dict(row) for row in cursor.fetchall()]
                    
                    # Fetch edges
                    cursor.execute("SELECT id, source_id, target_id, relation_type, timestamp FROM edges ORDER BY id DESC LIMIT 1000")
                    edges = [dict(row) for row in cursor.fetchall()]
                    
                self.wfile.write(json.dumps({
                    "nodes": entities,
                    "edges": edges
                }).encode('utf-8'))
            except Exception as e:
                try:
                    self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
                except Exception:
                    logging.exception("Failed to send knowledge graph error")
            return

        elif path_base == '/api/files':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            files = agent.memory.list_workspace_files()
            try:
                self.wfile.write(json.dumps({"files": files}).encode('utf-8'))
            except Exception:
                logging.exception("Failed to send files list")
            return

        elif path_base == '/api/lectura':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            lectura_dir = os.path.join(agent.base_dir, "lectura")
            files = []
            if os.path.exists(lectura_dir):
                files = os.listdir(lectura_dir)
            
            try:
                self.wfile.write(json.dumps({"files": files}).encode('utf-8'))
            except Exception:
                logging.exception("Failed to send lectura files")
            return

        elif path_base == '/api/mcp':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            mcp_tools = list(getattr(agent.brain, 'MCP_TOOLS', {}).keys())
            try:
                self.wfile.write(json.dumps({"servers": [{"name": "Local Tools", "status": "online", "tools": mcp_tools}]}).encode('utf-8'))
            except Exception:
                logging.exception("Failed to send MCP tools")
            return

        elif path_base == '/api/metrics':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            try:
                from src import metrics as metrics_mod
                metrics_mod.update_resource_usage()
                self.wfile.write(json.dumps(metrics_mod.get_metrics()).encode('utf-8'))
            except Exception as e:
                try:
                    self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
                except Exception:
                    logging.exception("Failed to send metrics")
            return

        return super().do_GET()

    used_nonces = {}
    nonce_lock = threading.Lock()

    def _verify_signature(self, post_data: bytes) -> bool:
        if os.environ.get("ANTI_MANAGED") != "1":
            return True # Permitir acceso si no es gestionado por Go
            
        nonce = self.headers.get('X-Anti-Nonce')
        signature = self.headers.get('X-Anti-Signature')
        
        if not nonce or not signature:
            return False
            
        import hmac
        import hashlib
        payload_to_sign = nonce.encode('utf-8') + b"." + post_data
        expected_mac = hmac.new(SHARED_SECRET, payload_to_sign, hashlib.sha256).hexdigest()
        
        if not hmac.compare_digest(expected_mac, signature):
            return False
            
        with self.nonce_lock:
            now = time.time()
            stale = [n for n, ts in self.used_nonces.items() if now - ts > 300]
            for n in stale:
                del self.used_nonces[n]
            if nonce in self.used_nonces:
                return False
            self.used_nonces[nonce] = time.time()
            
        return True

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        MAX_BODY_SIZE = 10 * 1024 * 1024  # 10MB
        if content_length > MAX_BODY_SIZE:
            self.send_response(413)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Request too large"}).encode('utf-8'))
            return
        post_data = self.rfile.read(content_length)

        if not self._verify_signature(post_data):
            self.send_error(403, "Forbidden: Invalid Signature or Replay Attack detected")
            return

        path_base = self.path.split('?')[0]

        if path_base == '/api/chat':

            try:
                data = json.loads(post_data.decode('utf-8'))
                message = data.get('message', '')
                image_data = data.get('image', None)

                job_id = str(uuid.uuid4())
                with active_jobs_lock:
                    active_jobs[job_id] = {
                        "status": "processing",
                        "result": None
                    }

                thread = threading.Thread(target=background_agent_task, args=(job_id, message, image_data))
                thread.daemon = True
                thread.start()

                self.send_response(202)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"job_id": job_id}).encode('utf-8'))

            except json.JSONDecodeError:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Invalid JSON")
            return


def run_server(port=SERVER_PORT):
    global agent
    if agent is None:
        agent = AntiAgent()
    httpd = ThreadingHTTPServer(('127.0.0.1', port), APIHandler)
    url = f"http://localhost:{port}"
    print(f"Anti Web UI: {url}")
    if not os.environ.get("ANTI_NO_BROWSER"):
        try:
            webbrowser.open(url)
        except Exception:
            pass

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        httpd.server_close()


if __name__ == '__main__':
    run_server()

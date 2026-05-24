import os
import json
import webbrowser
import threading
import uuid
import asyncio
from http.server import HTTPServer, SimpleHTTPRequestHandler, ThreadingHTTPServer

# Corrected imports for the current structure
from src.agent import AntiAgent
from src.tools import read_file

agent = AntiAgent()
active_jobs = {}

# MCP servers storage
MCP_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory", "mcp_servers.json")

def load_mcps():
    if os.path.exists(MCP_FILE):
        try:
            with open(MCP_FILE, "r") as f:
                return json.load(f)
        except:
            return []
    return []

def save_mcps(mcps):
    os.makedirs(os.path.dirname(MCP_FILE), exist_ok=True)
    with open(MCP_FILE, "w") as f:
        json.dump(mcps, f, indent=2)


def background_agent_task(job_id, message, image_data):
    """Ejecuta el agente en segundo plano y guarda el resultado en active_jobs."""
    try:
        # handle_command is async
        response_obj = asyncio.run(agent.handle_command(message, image_data=image_data))
        
        if response_obj is None:
            response_obj = {"response": "Comando ejecutado.", "steps": []}
        if isinstance(response_obj, str):
            response_obj = {"response": response_obj, "steps": []}
            
        active_jobs[job_id]["status"] = "completed"
        active_jobs[job_id]["result"] = response_obj
    except Exception as e:
        active_jobs[job_id]["status"] = "failed"
        active_jobs[job_id]["error"] = str(e)


class APIHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Point to the web directory in extras/web
        web_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "extras", "web")
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
            job_id = path_base.replace('/api/job/', '')
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            job = active_jobs.get(job_id, {"status": "not_found"})
            try:
                self.wfile.write(json.dumps(job).encode('utf-8'))
            except:
                pass
            return

        if path_base == '/api/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            # Hybrid Memory Stats
            archive_stats = agent.memory.archive.get_stats() if hasattr(agent.memory, 'archive') else {"archived_engrams": 0}

            try:
                status = {
                    "connected": asyncio.run(agent.brain.check_connection()),
                    "agent_name": agent.config.get("agent_name", "Anti"),
                    "loaded_model": asyncio.run(agent.brain.get_model_info()),
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
                except:
                    pass
            return

        elif path_base == '/api/files':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            files = agent.memory.list_workspace_files()
            try:
                self.wfile.write(json.dumps({"files": files}).encode('utf-8'))
            except:
                pass
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
            except:
                pass
            return

        elif path_base == '/api/mcp':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            # Devolver lista de herramientas MCP registradas en el cerebro
            mcp_tools = list(getattr(agent.brain, 'MCP_TOOLS', {}).keys())
            try:
                self.wfile.write(json.dumps({"servers": [{"name": "Local Tools", "status": "online", "tools": mcp_tools}]}).encode('utf-8'))
            except:
                pass
            return

        elif path_base.startswith('/api/file/'):
            filename = path_base.replace('/api/file/', '')
            content = agent.memory.read_file(filename) if hasattr(agent.memory, 'read_file') else ""
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            try:
                self.wfile.write(json.dumps({"content": content}).encode('utf-8'))
            except:
                pass
            return

        return super().do_GET()

    def do_POST(self):
        path_base = self.path.split('?')[0]

        if path_base == '/api/chat':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)

            try:
                data = json.loads(post_data.decode('utf-8'))
                message = data.get('message', '')
                image_data = data.get('image', None)

                job_id = str(uuid.uuid4())
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


def run_server(port=8000):
    httpd = ThreadingHTTPServer(('', port), APIHandler)
    url = f"http://localhost:{port}"
    print(f"Anti Web UI: {url}")
    webbrowser.open(url) # Uncomment if you want auto-open

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        httpd.server_close()


if __name__ == '__main__':
    run_server()

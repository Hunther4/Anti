import os
import json
import webbrowser
import threading
import uuid
from http.server import HTTPServer, SimpleHTTPRequestHandler, ThreadingHTTPServer
from core.agent import AntiAgent

agent = AntiAgent()
active_jobs = {}


def background_agent_task(job_id, message, image_data):
    """Ejecuta el agente en segundo plano y guarda el resultado en active_jobs."""
    try:
        import asyncio
        # handle_command is now async
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
        web_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
        super().__init__(*args, directory=web_dir, **kwargs)

    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def do_GET(self):
        # Extract base path without query parameters (fixes cache-busting logic)
        path_base = self.path.split('?')[0]

        # Refresh logic
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
            except (BrokenPipeError, ConnectionResetError):
                pass
            return

        if path_base == '/api/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            import asyncio
            status = {
                "connected": asyncio.run(agent.brain.check_connection()),
                "agent_name": agent.config.get("agent_name", "Anti"),
                "loaded_model": asyncio.run(agent.brain.get_model_info()),
                "files_count": agent.memory.count_workspace_files(),
                "engrams_count": agent.memory.count_engrams(),
                "reasoner_mode": agent.reasoner_mode,
            }
            try:
                self.wfile.write(json.dumps(status).encode('utf-8'))
            except (BrokenPipeError, ConnectionResetError):
                pass
            return

        elif path_base == '/api/files':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            files = agent.memory.list_workspace_files()
            try:
                self.wfile.write(json.dumps({"files": files}).encode('utf-8'))
            except (BrokenPipeError, ConnectionResetError):
                pass
            return

        elif path_base.startswith('/api/file/'):
            filename = path_base.replace('/api/file/', '')
            from core.tools import read_file
            content = read_file(filename)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            try:
                self.wfile.write(json.dumps({"content": content}).encode('utf-8'))
            except (BrokenPipeError, ConnectionResetError):
                pass
            return

        elif path_base == '/api/lectura':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            lectura_path = os.path.join(agent.base_dir, "lectura")
            os.makedirs(lectura_path, exist_ok=True)
            files = sorted(os.listdir(lectura_path))
            try:
                self.wfile.write(json.dumps({"files": files}).encode('utf-8'))
            except (BrokenPipeError, ConnectionResetError):
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

                # Generar TICKET de trabajo
                job_id = str(uuid.uuid4())
                active_jobs[job_id] = {
                    "status": "processing",
                    "result": None
                }

                # Iniciar hilo de fondo
                thread = threading.Thread(target=background_agent_task, args=(job_id, message, image_data))
                thread.daemon = True
                thread.start()

                self.send_response(202) # Accepted
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"job_id": job_id}).encode('utf-8'))

            except json.JSONDecodeError:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Invalid JSON")
            return

        elif path_base == '/api/upload-lectura':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode('utf-8'))
                filename = os.path.basename(data.get('filename', 'documento.txt'))
                content = data.get('content', '')
                lectura_path = os.path.join(agent.base_dir, "lectura")
                os.makedirs(lectura_path, exist_ok=True)
                with open(os.path.join(lectura_path, filename), 'w', encoding='utf-8') as f:
                    f.write(content)
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "filename": filename}).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())
            return


def run_server(port=8000):
    # Usamos ThreadingHTTPServer para que las busquedas largas no bloqueen el status
    httpd = ThreadingHTTPServer(('', port), APIHandler)
    url = f"http://localhost:{port}"
    print(f"Servidor web en {url}")
    webbrowser.open(url)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nApagando servidor...")
        httpd.server_close()
    print("Servidor detenido.")


if __name__ == '__main__':
    run_server()

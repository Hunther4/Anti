import os
import json
import subprocess
import sys
import signal
import requests
import socket

# Global server process tracker for PID management
server_process = None

# Colors for a premium "bonito" look (HSL-matched terminal equivalents)
class Colors:
    BLUE = "\033[38;2;60;130;246m"      # Premium Blue
    GREEN = "\033[38;2;34;197;94m"      # Emerald Green
    YELLOW = "\033[38;2;234;179;8m"     # Gold Yellow
    RED = "\033[38;2;239;68;68m"        # Vibrant Red
    CYAN = "\033[38;2;6;182;212m"       # Cyan Glass
    PURPLE = "\033[38;2;168;85;247m"    # Cosmic Purple
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    END = "\033[0m"

CONFIG_PATH = "config.json"

def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "agent_name": "Anti",
        "provider": "auto",
        "model": None,
        "lm_studio_url": "http://127.0.0.1:1234/v1",
        "ollama_url": "http://127.0.0.1:11434"
    }

def save_config(config):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def is_port_open(port=8000):
    """Check if the local server port is open."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.5)
    try:
        s.connect(('127.0.0.1', port))
        s.close()
        return True
    except:
        return False


def safe_run(cmd, description="comando"):
    """
    Wrapper for subprocess.run with better error messages.
    Returns True if process completed successfully, False on error.
    """
    try:
        subprocess.run(cmd, check=True)
        return True
    except FileNotFoundError:
        print(f"{Colors.RED}[ERROR] No se encontró el ejecutable: {cmd[0] if cmd else '?'}{Colors.END}")
        print(f"{Colors.YELLOW}  → Contexto: {description}{Colors.END}")
        return False
    except subprocess.CalledProcessError as e:
        print(f"{Colors.RED}[ERROR] El comando falló con código {e.returncode}{Colors.END}")
        print(f"{Colors.YELLOW}  → Contexto: {description}{Colors.END}")
        print(f"{Colors.YELLOW}  → Comando: {' '.join(cmd)}{Colors.END}")
        return False
    except Exception as e:
        print(f"{Colors.RED}[ERROR] Excepción inesperada al ejecutar '{description}': {e}{Colors.END}")
        return False

def print_banner():
    print(f"{Colors.PURPLE}{Colors.BOLD}")
    print(" ▄▄▄·  ▐ ▄ ▄▄▄▄▄ ▪  ")
    print("▐█ ▀█ •█▌▐█•██  ██  ")
    print("▄█▀▀█ ▐█▐▐▌ ▐█.▪▐█· ")
    print("▐█ ▪▐▌██▐█▌ ▐█▌·▐█▌ ")
    print(" ▀  ▀ ▀▀ ▀▀  ▀  ▀▀▀ ")
    print(f"   {Colors.CYAN}--- CENTRO DE CONTROL CÓSMICO v1.4 ---{Colors.END}\n")

def get_api_server_status():
    if is_port_open(8000):
        try:
            r = requests.get("http://127.0.0.1:8000/api/status", timeout=0.5)
            if r.status_code == 200:
                data = r.json()
                return f"{Colors.GREEN}● ONLINE{Colors.END} (IA: {data.get('loaded_model', 'Desconocido')})"
        except:
            return f"{Colors.GREEN}● ONLINE{Colors.END} (Iniciando API)"
        return f"{Colors.GREEN}● ONLINE{Colors.END}"
    return f"{Colors.RED}○ OFFLINE{Colors.END}"

def manage_apis(config):
    while True:
        clear_screen()
        print_banner()
        print(f"{Colors.BOLD}🔌 GESTIÓN DE CONEXIONES API (¡Ponete las pilas!){Colors.END}\n")
        
        providers = ["openai", "deepseek", "gemini"]
        for p in providers:
            key = config.get(f"{p}_api_key", "No configurada")
            status = f"{Colors.GREEN}✅ Configurada{Colors.END}" if key != "No configurada" else f"{Colors.RED}❌ Faltante{Colors.END}"
            masked_key = f"{key[:8]}...{key[-8:]}" if key != "No configurada" and len(key) > 16 else key
            print(f" 🔹 {p.capitalize():<10} ➔ {status:<15} ({masked_key})")
        
        print(f"\n{Colors.BOLD}Opciones:{Colors.END}")
        print(f" {Colors.GREEN}1.{Colors.END} Actualizar/Agregar Clave API")
        print(f" {Colors.RED}0.{Colors.END} Volver al menú anterior")
        
        choice = input(f"\n{Colors.CYAN}Anti@Control > {Colors.END}").strip()
        
        if choice == "1":
            print(f"\n{Colors.BOLD}¿Qué API querés configurar, loco?{Colors.END}")
            for i, p in enumerate(providers, 1):
                print(f"  {Colors.YELLOW}{i}.{Colors.END} {p.capitalize()}")
            
            p_choice = input(f"\n{Colors.CYAN}Anti@Control > {Colors.END}").strip()
            try:
                idx = int(p_choice) - 1
                if 0 <= idx < len(providers):
                    p_name = providers[idx]
                    new_key = input(f"Ingresá la clave para {p_name.capitalize()}: ").strip()
                    if new_key:
                        config[f"{p_name}_api_key"] = new_key
                        save_config(config)
                        print(f"\n{Colors.GREEN}¡Listo, hermano! Clave guardada correctamente.{Colors.END}")
                else:
                    print(f"{Colors.RED}Opción inválida.{Colors.END}")
            except ValueError:
                print(f"{Colors.RED}Ingresá un número válido.{Colors.END}")
            input("\nPresioná Enter para continuar...")
            
        elif choice == "0":
            break

def choose_model(config):
    while True:
        clear_screen()
        print_banner()
        print(f"{Colors.BOLD}🤖 SELECCIÓN DE MODELO DE IA{Colors.END}\n")
        
        provider = config.get("provider", "auto")
        print(f"  ⚙️  Proveedor: {Colors.CYAN}{Colors.BOLD}{provider.upper()}{Colors.END}")
        print(f"  🧠  Modelo:    {Colors.CYAN}{Colors.BOLD}{config.get('model', 'Ninguno')}{Colors.END}\n")
        
        print(f"{Colors.BOLD}Opciones:{Colors.END}")
        print(f" {Colors.GREEN}1.{Colors.END} Cambiar Proveedor Activo")
        print(f" {Colors.GREEN}2.{Colors.END} Auto-detectar Modelos Locales")
        print(f" {Colors.GREEN}3.{Colors.END} Especificar Nombre de Modelo Manualmente")
        print(f" {Colors.RED}0.{Colors.END} Volver al menú anterior")
        
        choice = input(f"\n{Colors.CYAN}Anti@Control > {Colors.END}").strip()
        
        if choice == "1":
            providers = ["auto", "lmstudio", "ollama", "openai", "deepseek", "gemini"]
            print(f"\n{Colors.BOLD}Proveedores disponibles:{Colors.END}")
            for i, p in enumerate(providers, 1):
                print(f"  {Colors.YELLOW}{i}.{Colors.END} {p}")
            
            p_choice = input(f"\n{Colors.CYAN}Anti@Control > {Colors.END}").strip()
            try:
                idx = int(p_choice) - 1
                if 0 <= idx < len(providers):
                    config["provider"] = providers[idx]
                    save_config(config)
                    print(f"{Colors.GREEN}Proveedor actualizado a {providers[idx]}.{Colors.END}")
                else:
                    print(f"{Colors.RED}Opción inválida.{Colors.END}")
            except ValueError:
                print(f"{Colors.RED}Ingresá un número válido.{Colors.END}")
            input("\nPresioná Enter para continuar...")
            
        elif choice == "2":
            models = []
            try:
                # Intenta listar modelos de LM Studio
                url = config.get("lm_studio_url", "http://127.0.0.1:1234/v1")
                r = requests.get(f"{url}/models", timeout=1)
                if r.status_code == 200:
                    models = [m["id"] for m in r.json().get("data", [])]
            except:
                pass
                
            if not models:
                try:
                    # Intenta listar modelos de Ollama
                    url = config.get("ollama_url", "http://127.0.0.1:11434")
                    r = requests.get(f"{url}/api/tags", timeout=1)
                    if r.status_code == 200:
                        models = [m["name"] for m in r.json().get("models", [])]
                except:
                    pass
            
            if not models:
                print(f"\n{Colors.YELLOW}⚠️  No se detectaron servidores locales de Ollama o LM Studio activos.{Colors.END}")
            else:
                print(f"\n{Colors.BOLD}Modelos detectados en caliente:{Colors.END}")
                for i, m in enumerate(models, 1):
                    print(f"  {Colors.YELLOW}{i}.{Colors.END} {m}")
                
                m_choice = input(f"\n{Colors.CYAN}Anti@Control > {Colors.END}").strip()
                try:
                    idx = int(m_choice) - 1
                    if 0 <= idx < len(models):
                        config["model"] = models[idx]
                        save_config(config)
                        print(f"{Colors.GREEN}Modelo configurado: {models[idx]}{Colors.END}")
                    else:
                        print(f"{Colors.RED}Opción incorrecta.{Colors.END}")
                except ValueError:
                    print(f"{Colors.RED}Por favor, ingresá un número.{Colors.END}")
            input("\nPresioná Enter para continuar...")
            
        elif choice == "3":
            new_model = input("\nIngresá el nombre exacto de la IA (ej. gpt-4o, deepseek-coder): ").strip()
            if new_model:
                config["model"] = new_model
                save_config(config)
                print(f"{Colors.GREEN}Modelo configurado a {new_model}.{Colors.END}")
            input("\nPresioná Enter para continuar...")
            
        elif choice == "0":
            break

def setup_system(config):
    clear_screen()
    print_banner()
    print(f"{Colors.BOLD}⚙️  DIAGNÓSTICO DEL SISTEMA (¿Está todo en orden?){Colors.END}\n")
    
    files = ["config.json", "requirements.txt", "main.py", "server.py", "src/document_parser.py"]
    all_ok = True
    for f in files:
        status = f"{Colors.GREEN}✅ OK{Colors.END}" if os.path.exists(f) else f"{Colors.RED}❌ FALTANTE{Colors.END}"
        print(f"  📂 {f:<25} ➔ {status}")
        if not os.path.exists(f):
            all_ok = False
            
    if all_ok:
        print(f"\n{Colors.GREEN}{Colors.BOLD}¡Excelente, loco! Todos los archivos críticos de la v1.4 están listos.{Colors.END}")
    else:
        print(f"\n{Colors.RED}¡Atención! Faltan archivos de la instalación original.{Colors.END}")
        
    input("\nPresioná Enter para continuar...")

def show_knowledge_graph(config):
    clear_screen()
    print_banner()
    print(f"{Colors.BOLD}🕸️  GRAFO DE CONOCIMIENTO (Relaciones de Engrams){Colors.END}\n")
    
    db_path = "workspace/memory/archive.db"
    if not os.path.exists(db_path):
        print(f"{Colors.YELLOW}⚠️  Aún no hay base de datos de memoria iniciada en workspace/memory/archive.db{Colors.END}")
        print("Hacé que Anti corra alguna tarea primero para crear engrams y extraer entidades.")
        input("\nPresioná Enter para volver...")
        return
        
    try:
        import sqlite3
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            # Obtener las 20 entidades más recientes
            cursor.execute("SELECT id, entity_type, value FROM entities ORDER BY id DESC LIMIT 20")
            nodes = cursor.fetchall()
            
            if not nodes:
                print(f"{Colors.YELLOW}No hay entidades guardadas en el Knowledge Graph todavía.{Colors.END}")
                print("Consejo: Hacé que Anti guarde algunos Engrams para extraer entidades automáticamente.")
                input("\nPresioná Enter para volver...")
                return
                
            print(f"{Colors.BOLD}Nodos de Conocimiento Recientes y sus Relaciones:{Colors.END}")
            print(" ─" * 25)
            for node_id, entity_type, value in nodes:
                # Buscar relaciones (edges) donde este nodo es la fuente (source)
                cursor.execute(
                    "SELECT target_id, relation_type FROM edges WHERE source_id = ?",
                    (node_id,)
                )
                edges = cursor.fetchall()
                
                rel_str = ""
                if edges:
                    rel_list = []
                    for target_id, rel_type in edges:
                        cursor.execute("SELECT value FROM entities WHERE id = ?", (target_id,))
                        target_val = cursor.fetchone()
                        if target_val:
                            rel_list.append(f"➔ ({rel_type}) ➔ {Colors.CYAN}{Colors.BOLD}{target_val[0]}{Colors.END}")
                    rel_str = " " + ", ".join(rel_list)
                
                print(f"  ● [{entity_type.upper()}] {Colors.GREEN}{value}{Colors.END}{rel_str}")
            print(" ─" * 25)
    except Exception as e:
        print(f"{Colors.RED}Error al leer el grafo de la base de datos: {e}{Colors.END}")
        
    input("\nPresioná Enter para continuar...")

def main():
    global server_process
    config = load_config()
    
    while True:
        clear_screen()
        print_banner()

        # Dashboard Panel
        server_status = get_api_server_status()
        server_pid_str = f" (PID: {server_process.pid})" if server_process and server_process.poll() is None else ""
        print(f" 🤖  {Colors.BOLD}Agente:{Colors.END}    {Colors.CYAN}{config.get('agent_name')}{Colors.END}")
        print(f" 🧠  {Colors.BOLD}Modelo:{Colors.END}    {Colors.CYAN}{config.get('model') or 'Sin seleccionar'}{Colors.END}")
        print(f" 🔌  {Colors.BOLD}API Host:{Colors.END}  {server_status}{server_pid_str}")
        print(" ─" * 25)

        print(f"{Colors.BOLD}MENU PRINCIPAL:{Colors.END}")
        print(f"  {Colors.CYAN}1.{Colors.END} 🖥️  Ejecutar Agente en Terminal (main.py)")
        print(f"  {Colors.CYAN}2.{Colors.END} 🌐  Iniciar Servidor API Backend (server.py)")
        print(f"  {Colors.CYAN}3.{Colors.END} 🔑  Gestionar Claves API y Credenciales")
        print(f"  {Colors.CYAN}4.{Colors.END} 🧠  Seleccionar Modelo de IA")
        print(f"  {Colors.CYAN}5.{Colors.END} ⚙️  Verificar Archivos y Diagnósticos")
        print(f"  {Colors.CYAN}6.{Colors.END} 🕸️  Ver Grafo de Conocimiento (Knowledge Graph)")
        if server_process and server_process.poll() is None:
            print(f"  {Colors.RED}7.{Colors.END} 🛑  Detener Servidor API (PID: {server_process.pid})")
        print(f"  {Colors.RED}0.{Colors.END} 🚪  Salir del Centro de Control")
        print(" ─" * 25)

        choice = input(f"\n{Colors.CYAN}Anti@Control > {Colors.END}").strip()

        if choice == "1":
            print(f"\n{Colors.BLUE}Iniciando Anti en modo terminal, ¡dale!...{Colors.END}\n")
            safe_run([sys.executable, "main.py"], "Terminal Agent (main.py)")
            input("\nPresioná Enter para volver al menú...")

        elif choice == "2":
            if is_port_open(8000):
                print(f"\n{Colors.YELLOW}⚠️  Puerto 8000 ya está en uso. No se puede iniciar el servidor.{Colors.END}")
                print(f"{Colors.YELLOW}   Detené el proceso actual o usá la opción 7 si lo controla este launcher.{Colors.END}")
            else:
                print(f"\n{Colors.BLUE}Iniciando servidor API en el puerto 8000...{Colors.END}")
                try:
                    server_process = subprocess.Popen(
                        [sys.executable, "server.py"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    print(f"{Colors.GREEN}✓ Servidor iniciado (PID: {server_process.pid}){Colors.END}")
                    print(f"{Colors.YELLOW}  Usá la opción 7 del menú para detenerlo.{Colors.END}")
                except Exception as e:
                    print(f"{Colors.RED}[ERROR] No se pudo iniciar el servidor: {e}{Colors.END}")
                    server_process = None
            input("\nPresioná Enter para volver al menú...")

        elif choice == "7":
            if server_process and server_process.poll() is None:
                print(f"\n{Colors.YELLOW}Deteniendo servidor (PID: {server_process.pid})...{Colors.END}")
                try:
                    server_process.send_signal(signal.SIGTERM)
                    server_process.wait(timeout=5)
                    print(f"{Colors.GREEN}✓ Servidor detenido correctamente.{Colors.END}")
                except subprocess.TimeoutExpired:
                    print(f"{Colors.YELLOW}⚠️  El servidor no respondió a SIGTERM, forzando...{Colors.END}")
                    server_process.kill()
                    server_process.wait()
                    print(f"{Colors.GREEN}✓ Servidor detenido (SIGKILL).{Colors.END}")
                except Exception as e:
                    print(f"{Colors.RED}[ERROR] Al detener el servidor: {e}{Colors.END}")
                server_process = None
            else:
                print(f"\n{Colors.YELLOW}⚠️  No hay un servidor en ejecución.{Colors.END}")
            input("\nPresioná Enter para volver al menú...")
            
        elif choice == "3":
            manage_apis(config)
            
        elif choice == "4":
            choose_model(config)
            
        elif choice == "5":
            setup_system(config)
            
        elif choice == "6":
            show_knowledge_graph(config)
            
        elif choice == "0":
            print(f"\n{Colors.BLUE}¡Hasta pronto, loco! Saliendo del Centro de Control de Anti.{Colors.END}\n")
            break
        else:
            print(f"{Colors.RED}Opción incorrecta.{Colors.END}")
            input("\nPresioná Enter para continuar...")

if __name__ == "__main__":
    main()

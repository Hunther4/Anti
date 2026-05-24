import os
import json
import subprocess
import sys
import requests

# Colors for a "bonito" look
class Colors:
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
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

def print_banner():
    print(f"{Colors.CYAN}{Colors.BOLD}")
    print("=" * 50)
    print("   🤖 ANTI CONTROL CENTER v0.6")
    print("=" * 50)
    print(f"{Colors.END}")

def manage_apis(config):
    while True:
        clear_screen()
        print_banner()
        print(f"{Colors.BOLD}🔌 GESTIÓN DE CONEXIONES API{Colors.END}\n")
        
        providers = ["openai", "deepseek", "gemini"]
        for p in providers:
            key = config.get(f"{p}_api_key", "No configurada")
            status = f"{Colors.GREEN}✅{Colors.END}" if key != "No configurada" else f"{Colors.RED}❌{Colors.END}"
            print(f"{p.capitalize()}: {status} {key if key != 'No configurada' else 'Falta clave'}")
        
        print(f"\n{Colors.BOLD}Opciones:{Colors.END}")
        print("1. Actualizar/Agregar Clave API")
        print("0. Volver al menú")
        
        choice = input(f"\n{Colors.GREEN}Anti@Control > {Colors.END}").strip()
        
        if choice == "1":
            print(f"\n{Colors.BOLD}¿Qué API querés configurar?{Colors.END}")
            for i, p in enumerate(providers, 1):
                print(f"{i}. {p.capitalize()}")
            
            p_choice = input(f"\n{Colors.GREEN}Anti@Control > {Colors.END}").strip()
            try:
                idx = int(p_choice) - 1
                if 0 <= idx < len(providers):
                    p_name = providers[idx]
                    new_key = input(f"Ingresá la clave para {p_name.capitalize()}: ").strip()
                    config[f"{p_name}_api_key"] = new_key
                    save_config(config)
                    print(f"{Colors.GREEN}Clave guardada correctamente.{Colors.END}")
                else:
                    print(f"{Colors.RED}Opción inválida.{Colors.END}")
            except ValueError:
                print(f"{Colors.RED}Por favor, ingresá un número.{Colors.END}")
            input("\nPresioná Enter para continuar...")
            
        elif choice == "0":
            break

def choose_model(config):
    while True:
        clear_screen()
        print_banner()
        print(f"{Colors.BOLD}🤖 SELECCIÓN DE MODELO{Colors.END}\n")
        
        provider = config.get("provider", "auto")
        print(f"Proveedor actual: {Colors.CYAN}{provider}{Colors.END}")
        print(f"Modelo actual: {Colors.CYAN}{config.get('model', 'Ninguno')}{Colors.END}\n")
        
        print(f"{Colors.BOLD}Opciones:{Colors.END}")
        print("1. Cambiar Proveedor")
        print("2. Elegir Modelo (Auto-detectar Locales)")
        print("3. Escribir Nombre de Modelo Manualmente")
        print("0. Volver al menú")
        
        choice = input(f"\n{Colors.GREEN}Anti@Control > {Colors.END}").strip()
        
        if choice == "1":
            providers = ["auto", "lmstudio", "ollama", "openai", "deepseek", "gemini"]
            print(f"\n{Colors.BOLD}Proveedores disponibles:{Colors.END}")
            for i, p in enumerate(providers, 1):
                print(f"{i}. {p}")
            
            p_choice = input(f"\n{Colors.GREEN}Anti@Control > {Colors.END}").strip()
            try:
                idx = int(p_choice) - 1
                if 0 <= idx < len(providers):
                    config["provider"] = providers[idx]
                    save_config(config)
                    print(f"{Colors.GREEN}Proveedor actualizado a {providers[idx]}.{Colors.END}")
                else:
                    print(f"{Colors.RED}Opción inválida.{Colors.END}")
            except ValueError:
                print(f"{Colors.RED}Por favor, ingresá un número.{Colors.END}")
            input("\nPresioná Enter para continuar...")
            
        elif choice == "2":
            # Try to list local models
            models = []
            try:
                # Try LM Studio/OpenAI compatible
                url = config.get("lm_studio_url", "http://127.0.0.1:1234/v1")
                r = requests.get(f"{url}/models", timeout=2)
                if r.status_code == 200:
                    data = r.json()
                    models = [m["id"] for m in data.get("data", [])]
            except:
                pass
            
            if not models:
                print(f"{Colors.RED}No se encontraron modelos locales disponibles.{Colors.END}")
            else:
                print(f"\n{Colors.BOLD}Modelos encontrados:{Colors.END}")
                for i, m in enumerate(models, 1):
                    print(f"{i}. {m}")
                
                m_choice = input(f"\n{Colors.GREEN}Anti@Control > {Colors.END}").strip()
                try:
                    idx = int(m_choice) - 1
                    if 0 <= idx < len(models):
                        config["model"] = models[idx]
                        save_config(config)
                        print(f"{Colors.GREEN}Modelo actualizado a {models[idx]}.{Colors.END}")
                    else:
                        print(f"{Colors.RED}Opción inválida.{Colors.END}")
                except ValueError:
                    print(f"{Colors.RED}Por favor, ingresá un número.{Colors.END}")
            input("\nPresioná Enter para continuar...")
            
        elif choice == "3":
            new_model = input("Ingresá el nombre exacto del modelo (ej. deepseek-chat, gpt-4o): ").strip()
            if new_model:
                config["model"] = new_model
                save_config(config)
                print(f"{Colors.GREEN}Modelo actualizado a {new_model}.{Colors.END}")
            input("\nPresioná Enter para continuar...")
            
        elif choice == "0":
            break

def setup_system(config):
    clear_screen()
    print_banner()
    print(f"{Colors.BOLD}⚙️ INSTALACIÓN Y SETUP{Colors.END}\n")
    print("Verificando archivos base...")
    
    files_to_check = ["config.json", "requirements.txt", "main.py", "server.py"]
    all_ok = True
    for f in files_to_check:
        if os.path.exists(f):
            print(f"  {Colors.GREEN}✅{Colors.END} {f}")
        else:
            print(f"  {Colors.RED}❌{Colors.END} {f} (Faltante)")
            all_ok = False
    
    if all_ok:
        print(f"\n{Colors.GREEN}El sistema está correctamente instalado y listo para usar.{Colors.END}")
    else:
        print(f"\n{Colors.RED}Faltan archivos críticos. Ejecutá el script de instalación.{Colors.END}")
    
    input("\nPresioná Enter para volver...")

def main():
    config = load_config()
    
    while True:
        clear_screen()
        print_banner()
        
        print(f" Agente: {Colors.BOLD}{config.get('agent_name')}{Colors.END}")
        print(f" Modelo: {Colors.BOLD}{config.get('model') or 'No seleccionado'}{Colors.END}")
        print(f" Proveedor: {Colors.BOLD}{config.get('provider')}{Colors.END}")
        print("\n" + "-" * 50)
        print(f"{Colors.BOLD}MENU PRINCIPAL:{Colors.END}")
        print(f" 1. 🖥️  {Colors.CYAN}Terminal{Colors.END} (Ejecutar Anti)")
        print(f" 2. 🌐  {Colors.CYAN}Web Host{Colors.END} (Ejecutar servidor)")
        print(f" 3. 🔌  {Colors.CYAN}Conexiones API{Colors.END} (Gestionar claves)")
        print(f" 4. 🤖  {Colors.CYAN}Elegir Modelo{Colors.END} (Seleccionar IA)")
        print(f" 5. ⚙️  {Colors.CYAN}Instalación/Setup{Colors.END} (Configuración)")
        print(f" 0. 🚪  {Colors.RED}Salir{Colors.END}")
        print("-" * 50)
        
        choice = input(f"\n{Colors.GREEN}Anti@Control > {Colors.END}").strip()
        
        if choice == "1":
            print(f"{Colors.BLUE}Lanzando Anti en modo terminal...{Colors.END}")
            # Use sys.executable to run main.py in the same environment
            subprocess.run([sys.executable, "main.py"])
            input("\nPresioná Enter para volver al menú...")
            
        elif choice == "2":
            print(f"{Colors.BLUE}Lanzando servidor web...{Colors.END}")
            # Server is typically a long-running process. 
            # We run it as a subprocess and wait for user to kill it or use Ctrl+C
            try:
                subprocess.run([sys.executable, "server.py"])
            except KeyboardInterrupt:
                print(f"\n{Colors.YELLOW}Servidor detenido por el usuario.{Colors.END}")
            input("\nPresioná Enter para volver al menú...")
            
        elif choice == "3":
            manage_apis(config)
            
        elif choice == "4":
            choose_model(config)
            
        elif choice == "5":
            setup_system(config)
            
        elif choice == "0":
            print(f"{Colors.BLUE}Saliendo del centro de control. ¡Hasta pronto!{Colors.END}")
            break
        else:
            print(f"{Colors.RED}Opción no válida.{Colors.END}")
            input("\nPresioná Enter para continuar...")

if __name__ == "__main__":
    main()

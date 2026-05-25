import re
from src.plugin_manager import anti_tool
import src.tools as tools_lib
import asyncio

@anti_tool(name="SEARCH", description="Busca en la web. (Usa Wave Search)")
def search_tool(raw_args: str):
    return tools_lib.duckduckgo_search(raw_args.strip())

ALLOWED_COMMANDS = {"ls", "pwd", "cat", "head", "tail", "echo", "date", "whoami", "which", "python3", "python", "pip", "npm", "go", "cargo", "node", "curl", "wget", "git", "docker", "make"}

@anti_tool(name="RUN", description="Ejecuta un comando de bash en el entorno seguro local.")
def run_tool(raw_args: str):
    cmd = raw_args.strip()
    base_cmd = cmd.split()[0] if cmd else ""
    if base_cmd not in ALLOWED_COMMANDS:
        return f"[ERROR] Comando '{base_cmd}' no permitido. Usá uno de: {', '.join(sorted(ALLOWED_COMMANDS))}"
    return tools_lib.run_local_command(cmd, timeout=30)

@anti_tool(name="WRITE", description="Crea o edita archivos locales. Formato recomendado:\nruta/archivo\n---\ncontenido\n\n(O el formato heredado: ruta/archivo | contenido)")
def write_tool(raw_args: str):
    raw_args = raw_args.strip()
    
    # Estrategia 1: Delimitador multilínea robusto
    if "\n---\n" in raw_args:
        parts = raw_args.split("\n---\n", 1)
        return tools_lib.write_file(parts[0].strip(), parts[1].strip())
        
    # Estrategia 2: Delimitador con encabezado FILE: o PATH:
    if raw_args.startswith("FILE:") or raw_args.startswith("PATH:"):
        lines = raw_args.split("\n", 1)
        if len(lines) > 1:
            header = lines[0].replace("FILE:", "").replace("PATH:", "").strip()
            content = lines[1].strip()
            # Limpiar bloques de código markdown si existen
            content = re.sub(r"^```[a-zA-Z0-9]*\n", "", content)
            content = re.sub(r"\n```$", "", content)
            return tools_lib.write_file(header, content)

    # Estrategia 3: Fallback legado por barra vertical
    if "|" in raw_args:
        parts = raw_args.split("|", 1)
        return tools_lib.write_file(parts[0].strip(), parts[1].strip())
        
    return "[ERROR] Formato incorrecto para WRITE. Usá el formato recomendado:\nruta/archivo\n---\ncontenido"

@anti_tool(name="READ", description="Lee archivos locales del workspace.")
def read_tool(raw_args: str):
    return tools_lib.read_file(raw_args.strip())

@anti_tool(name="FETCH", description="Lee el contenido en texto plano de una URL.")
def fetch_tool(raw_args: str):
    return tools_lib.fetch_url_text(raw_args.strip())

@anti_tool(name="RESEARCH", description="Investigación profunda autónoma. Retorna un informe ultra detallado.")
async def research_tool(raw_args: str):
    return await tools_lib.autonomous_research(raw_args.strip())

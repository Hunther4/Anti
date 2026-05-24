from src.plugin_manager import anti_tool
import src.tools as tools_lib
import asyncio

@anti_tool(name="SEARCH", description="Busca en la web. (Usa Wave Search)")
def search_tool(raw_args: str):
    return tools_lib.duckduckgo_search(raw_args.strip())

@anti_tool(name="RUN", description="Ejecuta un comando de bash en el entorno seguro local.")
def run_tool(raw_args: str):
    return tools_lib.run_local_command(raw_args.strip())

@anti_tool(name="WRITE", description="Crea o edita archivos locales. Formato: nombre.md | contenido")
def write_tool(raw_args: str):
    if "|" not in raw_args:
        return "[ERROR] Formato incorrecto para WRITE. Usa: ruta/archivo | contenido"
    parts = raw_args.split("|", 1)
    return tools_lib.write_file(parts[0].strip(), parts[1].strip())

@anti_tool(name="READ", description="Lee archivos locales del workspace.")
def read_tool(raw_args: str):
    return tools_lib.read_file(raw_args.strip())

@anti_tool(name="FETCH", description="Lee el contenido en texto plano de una URL.")
def fetch_tool(raw_args: str):
    return tools_lib.fetch_url_text(raw_args.strip())

@anti_tool(name="RESEARCH", description="Investigación profunda autónoma. Retorna un informe ultra detallado.")
async def research_tool(raw_args: str):
    return await tools_lib.autonomous_research(raw_args.strip())

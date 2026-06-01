"""
CommandHandler — CLI command routing, MCP management, admin commands, and UI helpers.
"""

import os
import re
import json
import shutil
import subprocess
import asyncio
from src.logger import AppLogger, Colors
from src import metrics

app_logger = AppLogger(__name__)


# --- Help & UI ---

HELP_TEXT = """
ANTI-AGENT — COMANDOS

  [Chat]
    Escribi cualquier pregunta y el agente responde.
    search <query>  Fuerza una busqueda web inmediata.

  [Plugins & Herramientas]
    plugins         Lista todos los plugins y herramientas cargadas en Anti.

  [MCP - Model Capability Protocol]
    mcp list          Lista todos los MCPs instalados
    mcp install <id>  Instala un nuevo MCP
    mcp remove <id>   Remueve un MCP instalado
    mcp help <id>     Muestra ayuda de un MCP

  [Sistema]
    reasoner    Activa/desactiva auto-critica de respuestas.
    reflect     Analiza experiencias pasadas y genera reglas (evolucion).
    memories    Muestra un resumen de la memoria del agente.
    engra       Lista todos los engrams (conocimiento persistente).
    compact     Comprime la memoria de patrones.
    consolidate Inicia el mantenimiento autonomo y purga de datos.
    renew / /r  Reinicia el servidor y aplica las ultimas actualizaciones.
    forget      Borra toda la memoria.
    status      Estado del sistema.
    exit/quit   Apagar.
"""


def show_help():
    print(f"{Colors.CYAN}{HELP_TEXT}{Colors.END}")
    return HELP_TEXT


def show_memories(memory):
    logs = memory.get_recent_logs(5)
    patterns = memory.load_patterns()
    engrams_count = memory.count_engrams()
    summary = f"""
MEMORIA DEL AGENTE
  Logs recientes: {len(logs)}
  Patrones guardados: {'Si' if patterns.strip() else 'No'}
  Engrams almacenados: {engrams_count}
"""
    print(f"{Colors.GREEN}{summary}{Colors.END}")
    return summary


def list_engrams(memory):
    engrams_path = memory.engrams_path
    if not os.path.exists(engrams_path):
        return "No hay engrams guardados."

    files = [f for f in os.listdir(engrams_path) if f.endswith(".json")]
    if not files:
        return "No hay engrams guardados."

    output = ["LISTA DE ENGRAMS (CONOCIMIENTO PERSISTENTE)"]
    for filename in files:
        filepath = os.path.join(engrams_path, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                topic = data.get("topic", filename)
                content = data.get("content", "")
                summary = content[:100] + "..." if len(content) > 100 else content
                output.append(f"- {topic}: {summary}")
        except (json.JSONDecodeError, IOError) as e:
            app_logger.warning(f"Error reading engram {filename}: {e}")

    res = "\n".join(output)
    print(f"{Colors.GREEN}{res}{Colors.END}")
    return res


def list_plugins(plugin_manager):
    title = f"\n{Colors.CYAN}{Colors.BOLD}PLUGINS & HERRAMIENTAS ACTIVAS EN ANTI{Colors.END}\n"
    lines = [title]
    if plugin_manager and plugin_manager.tools:
        for name, tool in plugin_manager.tools.items():
            desc = tool.get("description", "Sin descripcion")
            lines.append(f"  {Colors.GREEN}{Colors.BOLD}• {name}{Colors.END}: {desc}")
    else:
        lines.append(f"  {Colors.YELLOW}No se encontraron plugins dinamicos cargados.{Colors.END}")
    lines.append("")
    result = "\n".join(lines)
    print(result)
    return result


def toggle_reasoner(reasoner_mode):
    new_mode = not reasoner_mode
    status = "ACTIVADO" if new_mode else "DESACTIVADO"
    msg = f"Modo Reasoner: {status}"
    print(f"{Colors.YELLOW}[*] {msg}{Colors.END}")
    return msg, new_mode


async def show_status(brain, memory, context_mgr, reasoner_mode):
    connected = await brain.check_connection()
    conn_str = "Conectado" if connected else "Desconectado"
    logs = memory.get_recent_logs(1000)
    reasoner_status = "ON" if reasoner_mode else "OFF"

    ctx_stats = context_mgr.get_advanced_stats()
    load_percent = context_mgr.usage_percent
    integrity_level = context_mgr.get_load_level()

    status_text = f"""
ESTADO DEL SISTEMA
  Proveedor:        {conn_str}
  Modo Reasoner:    {reasoner_status}
  Skills:           {len(memory.skills.skills)} activas
  Experiencias:     {len(logs)} logs registrados
  Workspace:        {memory.count_workspace_files()} archivos
  Engrams:          {memory.count_engrams()} memorias

  [Context Integrity]
  Carga Actual:     {load_percent}% ({integrity_level})
  Eficiencia:       {ctx_stats['efficiency_score']}%
  Tokens Salvados:  {context_mgr.tokens_saved}
"""
    print(status_text)
    return status_text


# --- MCP Commands ---

def handle_mcp_command(args, memory):
    parts = args.strip().split(maxsplit=1)
    if not parts:
        return "MCP — Uso: mcp <list|install|remove|help> [id]"

    action = parts[0].lower()
    mcp_id = parts[1].strip() if len(parts) > 1 else ""

    if action == "list":
        return _mcp_list(memory)
    elif action == "install":
        if not mcp_id:
            return "MCP install — Uso: mcp install <id>"
        return _mcp_install(mcp_id, memory)
    elif action == "remove":
        if not mcp_id:
            return "MCP remove — Uso: mcp remove <id>"
        return _mcp_remove(mcp_id, memory)
    elif action == "help":
        if not mcp_id:
            return "MCP help — Uso: mcp help <id>"
        return _mcp_help(mcp_id, memory)
    else:
        return f"MCP: comando '{action}' no reconocido. Usa: list, install, remove, help"


def _mcp_list(memory):
    skills_dir = memory.skills_dir
    if not os.path.exists(skills_dir):
        return "No hay MCPs disponibles."

    folders = [f for f in os.listdir(skills_dir)
               if os.path.isdir(os.path.join(skills_dir, f))]

    if not folders:
        return "No hay MCPs instalados."

    lines = ["MCPs instalados:", ""]
    for folder in sorted(folders):
        skill_path = os.path.join(skills_dir, folder, "SKILL.md")
        if os.path.exists(skill_path):
            try:
                with open(skill_path, "r", encoding="utf-8") as f:
                    content = f.read()
                name = folder
                description = ""
                if content.startswith("---"):
                    end_idx = content.find("\n---", 3)
                    if end_idx > 0:
                        fm_text = content[3:end_idx].strip()
                        for line in fm_text.splitlines():
                            if ":" in line:
                                key, _, val = line.partition(":")
                                if key.strip() == "name":
                                    name = val.strip()
                                elif key.strip() == "description":
                                    description = val.strip()
                lines.append(f"  • {name}" + (f" — {description}" if description else ""))
            except Exception as e:
                app_logger.debug(f"Error reading MCP SKILL.md for {folder}: {e}")
                lines.append(f"  • {folder}")
        else:
            lines.append(f"  • {folder}")

    return "\n".join(lines)


def _mcp_install(mcp_id, memory):
    safe_id = re.sub(r'[^a-zA-Z0-9_-]', '', mcp_id.lower()) or "unnamed-mcp"
    skills_dir = memory.skills_dir

    existing_path = os.path.join(skills_dir, safe_id, "SKILL.md")
    if os.path.exists(existing_path):
        return f"MCP '{mcp_id}' ya esta instalado."

    mcp_dir = os.path.join(skills_dir, safe_id)
    os.makedirs(mcp_dir, exist_ok=True)

    skill_path = os.path.join(mcp_dir, "SKILL.md")
    template = f"""---
name: {safe_id}
description: MCP instalado via mcp install
category: user-installed
---

# {safe_id}

Contenido del MCP instalado. Editar este archivo para personalizar el comportamiento.
"""
    with open(skill_path, "w", encoding="utf-8") as f:
        f.write(template)

    if hasattr(memory, "skills"):
        memory.skills.reload()

    return f"MCP '{mcp_id}' instalado correctamente en memory/skills/{safe_id}/"


def _mcp_remove(mcp_id, memory):
    safe_id = re.sub(r'[^a-zA-Z0-9_-]', '', mcp_id.lower()) or "unnamed-mcp"
    if not safe_id:
        return "[ERROR] Invalid MCP ID"
    skills_dir = memory.skills_dir
    mcp_dir = os.path.join(skills_dir, safe_id)

    if not os.path.exists(mcp_dir):
        return f"MCP '{mcp_id}' no encontrado."

    try:
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(mcp_dir):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)
        app_logger.info(f"Removing MCP {safe_id}, directory size: {total_size} bytes")
    except Exception as e:
        app_logger.debug(f"Could not calculate size for MCP {safe_id}: {e}")

    shutil.rmtree(mcp_dir)

    if hasattr(memory, "skills"):
        memory.skills.reload()

    return f"MCP '{mcp_id}' removido correctamente."


def _mcp_help(mcp_id, memory):
    safe_id = re.sub(r'[^a-zA-Z0-9_-]', '-', mcp_id.lower())
    skills_dir = memory.skills_dir
    skill_path = os.path.join(skills_dir, safe_id, "SKILL.md")

    if not os.path.exists(skill_path):
        return f"MCP '{mcp_id}' no encontrado."

    try:
        with open(skill_path, "r", encoding="utf-8") as f:
            content = f.read()
        return f"=== MCP: {safe_id} ===\n\n{content}"
    except Exception as e:
        return f"Error leyendo MCP '{mcp_id}': {e}"


# --- Admin Commands ---

def admin_command(cmd, base_dir):
    """Admin: delete and move files across workspace/engrams/lectura."""
    print(f"{Colors.RED}[!] Modo Admin activado.{Colors.END}")
    parts = cmd.strip().split(maxsplit=2)

    if len(parts) < 3:
        return (
            "ADMIN — Comandos disponibles:\n"
            "  admin delete <nombre_archivo>   — Elimina un archivo del workspace, engrams o lectura\n"
            "  admin move <archivo> <destino>  — Mueve un archivo a workspace, engrams o lectura"
        )

    action = parts[1].lower()

    if action == "delete":
        target = parts[2].strip()
        safe_name = os.path.basename(target)
        search_dirs = [
            ("workspace", os.path.join(base_dir, "workspace")),
            ("engrams", os.path.join(base_dir, "memory", "engrams")),
            ("lectura", os.path.join(base_dir, "lectura")),
        ]
        for label, d in search_dirs:
            path = os.path.join(d, safe_name)
            if os.path.exists(path) and os.path.isfile(path):
                os.remove(path)
                print(f"{Colors.RED}[!] Eliminado: {path}{Colors.END}")
                return f"[ADMIN] Archivo '{safe_name}' eliminado de {label}/."
        return f"[ADMIN] No encontre '{safe_name}' en workspace, engrams ni lectura."

    elif action == "move":
        if len(parts) < 4:
            sub = cmd.strip().split(maxsplit=3)
            if len(sub) < 4:
                return "[ADMIN] Uso: admin move <archivo> <destino> (destino: workspace | engrams | lectura)"
            parts = sub

        src_name = os.path.basename(parts[2].strip())
        dst_label = parts[3].strip().lower().rstrip("/")

        dest_map = {
            "workspace": os.path.join(base_dir, "workspace"),
            "engrams": os.path.join(base_dir, "memory", "engrams"),
            "lectura": os.path.join(base_dir, "lectura"),
        }
        if dst_label not in dest_map:
            return f"[ADMIN] Destino invalido '{dst_label}'. Usa: workspace | engrams | lectura"

        src_path = None
        for d in dest_map.values():
            candidate = os.path.join(d, src_name)
            if os.path.exists(candidate):
                src_path = candidate
                break

        if not src_path:
            return f"[ADMIN] No encontre '{src_name}' en ninguna carpeta."

        dst_path = os.path.join(dest_map[dst_label], src_name)
        shutil.move(src_path, dst_path)
        print(f"{Colors.GREEN}[+] Movido: {src_path} -> {dst_path}{Colors.END}")
        return f"[ADMIN] '{src_name}' movido a {dst_label}/."

    else:
        return f"[ADMIN] Accion '{action}' no reconocida. Usa: delete | move"


# --- Force Search ---

async def force_search(query, _process_fn):
    """Force a web search and process the results."""
    from src.tools import duckduckgo_search

    time_period = None
    if query.endswith("/d"):
        time_period = "d"
        query = query[:-2].strip()
    elif query.endswith("/w"):
        time_period = "w"
        query = query[:-2].strip()
    elif query.endswith("/m"):
        time_period = "m"
        query = query[:-2].strip()

    print(f"{Colors.YELLOW}[*] Forzando busqueda web ({time_period or 'todo'}): {query}...{Colors.END}")
    search_results = duckduckgo_search(query, time_period=time_period)

    context = f"El usuario forzo una busqueda web para: {query}\n\nResultados:\n{search_results}\n\nResponde en base a esto."
    return await _process_fn(context)


# --- Master Router ---

async def handle_command(cmd, agent, image_data=None):
    """
    Master command router. Dispatches to the appropriate handler.
    agent is the AntiAgent instance (for accessing state).
    """
    cmd_lower = cmd.lower().strip()

    if cmd_lower == "help":
        return show_help()
    elif cmd_lower == "status":
        return await show_status(agent.brain, agent.memory, agent.context_mgr, agent.reasoner_mode)
    elif cmd_lower == "metrics":
        return metrics.get_metrics()
    elif cmd_lower == "reasoner":
        msg, agent.reasoner_mode = toggle_reasoner(agent.reasoner_mode)
        return msg
    elif cmd_lower == "reflect":
        findings = await agent._reflect()
        return f"Reflexion completada.\n\n{findings}"
    elif cmd_lower == "compact":
        await agent._compact_memory()
        return "Memoria compactada."
    elif cmd_lower == "forget":
        agent.memory.forget()
        print(f"{Colors.RED}[!] Memoria de patrones borrada.{Colors.END}")
        return "Memoria borrada."
    elif cmd_lower == "plugins":
        return list_plugins(agent.plugin_manager)
    elif cmd_lower == "memories":
        return show_memories(agent.memory)
    elif cmd_lower == "engra":
        return list_engrams(agent.memory)
    elif cmd_lower.startswith("search "):
        query = cmd[7:].strip()
        return await force_search(query, agent._process)
    elif cmd_lower == "consolidate":
        stats = await agent.consolidator.run_maintenance()
        return f"Consolidacion finalizada: {stats['deleted_decay']} purgados, {stats['consolidated_engrams']} sintetizados."
    elif cmd_lower == "renew" or cmd_lower == "/r":
        return await agent._renew_system()
    elif cmd_lower.startswith("mcp "):
        return handle_mcp_command(cmd[4:].strip(), agent.memory)
    elif cmd_lower.startswith("admin "):
        return admin_command(cmd, agent.base_dir)
    else:
        return await agent._process(cmd, image_data=image_data)

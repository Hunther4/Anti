import os
import json
import re
import asyncio
import logging
import subprocess
import shutil
import time
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.status import Status

from src.logger import AppLogger, Colors

from src.logger import AppLogger, Colors

logger = logging.getLogger(__name__)
app_logger = AppLogger(__name__)

from src.brain import Brain
from src.memory import MemoryManager
from src.context_manager import ContextManager
from src.scorer import PRMScorer
from src.evolver import SkillEvolver
from src.consolidator import MemoryConsolidator
from src.tools import duckduckgo_search, fetch_url_text, autonomous_research, write_file, read_file, run_local_command
from src import metrics
from prompts.system import build_system_prompt
from prompts.templates import REASONER_PROMPT, REFLECT_PROMPT, COMPACT_PROMPT, IMPORTANCE_PROMPT


def print_header(name="ANTI-AGENT"):
    print(f"{Colors.CYAN}{Colors.BOLD}")
    print("=" * 60)
    print(f"   {name.upper()}: AUTONOMOUS EVOLVING SYSTEM")
    print("=" * 60)
    print(f"{Colors.END}")


class AntiAgent:
    DEFAULT_LM_URL = "http://127.0.0.1:1234/v1"

    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.console = Console()

        self.config_path = os.path.join(self.base_dir, "config.json")
        self.config = self._load_config()

        # Inicializar proveedor (auto-detectar o específico)
        from src.providers import create_provider
        
        provider_type = self.config.get("provider", "auto")
        if provider_type == "auto":
            # Intentar detectar proveedor manualmente (sync path para __init__)
            try:
                import httpx
                detected_url = None
                with httpx.Client(timeout=2) as client:
                    for port in [1234, 11434, 8000, 8001]:
                        try:
                            endpoint = "/api/tags" if port == 11434 else "/v1/models"
                            url = f"http://127.0.0.1:{port}"
                            r = client.get(f"{url}{endpoint}")
                            if r.status_code == 200:
                                detected_url = url if port == 11434 else f"{url}/v1"
                                break
                        except Exception:
                            continue
                
                if detected_url:
                    if ":11434" in detected_url:
                        self.brain = create_provider("ollama", base_url=detected_url,
                            model=self.config.get("model"), timeout=self.config.get("timeout", 120))
                    else:
                        self.brain = create_provider("lmstudio", base_url=detected_url,
                            model=self.config.get("model"), timeout=self.config.get("timeout", 120))
                    logger.info(f"Proveedor auto-detectado: {type(self.brain).__name__}")
                else:
                    raise Exception("No provider found")
            except Exception as e:
                logger.warning(f"Auto-detección falló: {e}. Usando LM Studio por defecto.")
                self.brain = create_provider(
                    "lmstudio",
                    base_url=self.config.get("lm_studio_url", self.DEFAULT_LM_URL),
                    model=self.config.get("model")
                )
        else:
            # Proveedor específico
            url_config = self.config.get(f"{provider_type}_url", 
                          self.config.get("lm_studio_url", self.DEFAULT_LM_URL))
            api_key = self.config.get(f"{provider_type}_api_key")
            self.brain = create_provider(
                provider_type,
                base_url=url_config,
                model=self.config.get("model"),
                api_key=api_key
            )

        workspace_path = os.path.join(self.base_dir, "workspace")
        if not os.path.exists(workspace_path):
            os.makedirs(workspace_path)

        self.memory = MemoryManager(
            memory_path=os.path.join(self.base_dir, "memory"),
            workspace_path=workspace_path
        )

        # v0.6 Sentinel Core
        self.context_mgr = ContextManager(model_context_length=32000)
        
        self.is_running = True
        self.task_counter = 0
        self.history = []
        self.reasoner_mode = False

        # Autonomous Components
        url = self.config.get("lm_studio_url", self.DEFAULT_LM_URL)
        self.scorer = PRMScorer(prm_url=url, prm_model=self.brain.model)
        self.evolver = SkillEvolver(base_url=url, model="local-model")
        
        # Dynamic Plugin System
        from src.plugin_manager import PluginManager
        self.plugin_manager = PluginManager(plugins_dir=os.path.join(self.base_dir, "src/plugins"))
        self.consolidator = MemoryConsolidator(self.memory, self.evolver)
        self.last_maintenance_count = 0

    def _load_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "agent_name": "Anti",
            "max_iterations": 5,
            "personality": "Sos un agente autonomo avanzado."
        }

    async def close(self):
        """Gracefully closes all resources."""
        if hasattr(self, 'brain') and self.brain:
            if hasattr(self.brain, 'close'):
                await self.brain.close()
        if hasattr(self, 'scorer') and self.scorer:
            pass
        app_logger.info("AntiAgent resources closed successfully.")

    def render_markdown(self, text: str) -> str:
        """
        Renders basic markdown elements into gorgeous ANSI escape sequences.
        Prevents visual fatigue by replacing raw markers with clean layouts.
        """
        if not text:
            return ""
        
        lines = text.split("\n")
        rendered_lines = []
        in_code_block = False
        
        for line in lines:
            # Code block toggle
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                if in_code_block:
                    lang = line.replace("```", "").strip().upper() or "CODE"
                    rendered_lines.append(f"{Colors.GRAY}┌─── {lang} ──────────────────────────────────────{Colors.END}")
                else:
                    rendered_lines.append(f"{Colors.GRAY}└──────────────────────────────────────────────────{Colors.END}")
                continue
                
            if in_code_block:
                rendered_lines.append(f"{Colors.WHITE}{line}{Colors.END}")
                continue
                
            # Horizontal Rules
            if line.strip() in ("---", "***", "___"):
                rendered_lines.append(f"{Colors.CYAN}⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼{Colors.END}")
                continue
                
            # Headers
            if line.startswith("# "):
                header_text = line[2:].strip()
                rendered_lines.append(f"\n{Colors.CYAN}{Colors.BOLD}█ {header_text.upper()}{Colors.END}")
                rendered_lines.append(f"{Colors.CYAN}⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼{Colors.END}")
                continue
                
            if line.startswith("## "):
                header_text = line[3:].strip()
                rendered_lines.append(f"\n{Colors.BLUE}{Colors.BOLD}■ {header_text.upper()}{Colors.END}")
                continue
                
            if line.startswith("### "):
                header_text = line[4:].strip()
                rendered_lines.append(f"\n{Colors.MAGENTA}{Colors.BOLD}➔ {header_text}{Colors.END}")
                continue

            # Lists
            stripped = line.lstrip()
            indent_len = len(line) - len(stripped)
            
            is_bullet = False
            content = stripped
            if stripped.startswith("* ") or stripped.startswith("- "):
                is_bullet = True
                content = stripped[2:]
            elif stripped.startswith("*") and not stripped.startswith("**"):
                is_bullet = True
                content = stripped[1:]
            
            if is_bullet:
                indent = " " * indent_len
                bullet_char = "•" if indent_len == 0 else "◦"
                bullet_color = Colors.CYAN if indent_len == 0 else Colors.BLUE
                line = f"{indent}{bullet_color}{bullet_char}{Colors.END} {content}"

            # Bold & Italic
            line = re.sub(r"\*\*(.*?)\*\*", f"{Colors.BOLD}\\1{Colors.END}", line)
            line = re.sub(r"\*(.*?)\*", f"{Colors.BLUE}\\1{Colors.END}", line)
            line = re.sub(r"_(.*?)_", f"{Colors.BLUE}\\1{Colors.END}", line)
            
            rendered_lines.append(line)
            
        return "\n".join(rendered_lines)

    # --- CLI Loop ---

    def run(self):
        """Punto de entrada del CLI. Coordina banner, conexión y loop de input."""
        provider_name = type(self.brain).__name__.lower()
        is_local = "lmstudio" in provider_name or "ollama" in provider_name
        self._display_banner(is_local)
        self._check_startup_connection()
        self._input_loop(is_local)

    def _display_banner(self, is_local: bool):
        """Renderiza el banner ASCII y las tarjetas de diagnóstico de inicio."""
        # 1. ASCII Banner
        self.console.print(f"\n{Colors.CYAN}{Colors.BOLD}")
        self.console.print("     _   ___  __  __  ___  ")
        self.console.print("    /_\\ / _ \\|  \\/  |/ _ \\ ")
        self.console.print("   / _ \\ (_) | \\/| | (_) |")
        self.console.print("  /_/ \\_\\___/|_|  |_|___/ ")
        self.console.print(f"{Colors.END}{Colors.WHITE}  v1.6 Quantum{Colors.END}")
        self.console.print(f"{Colors.CYAN}{'─' * 40}{Colors.END}\n")
        
        # 2. Tarjetas de diagnóstico
        provider_label = self.config.get("provider", "auto").upper()
        model_label = self.config.get("model") or "Auto-detectado"
        db_path = os.path.join(self.base_dir, "memory/cold_archive.db")
        try:
            db_size_kb = int(os.path.getsize(db_path) / 1024) if os.path.exists(db_path) else 0
        except Exception:
            db_size_kb = 0
        
        plugins_count = len(self.plugin_manager.tools) if hasattr(self, "plugin_manager") else 5
        prm_status = "[green]ACTIVADO 🟢[/]" if self.config.get("enable_prm_scorer", True) else "[red]DESACTIVADO 🔴[/]"
        
        diag_text = (
            f"🤖 [bold]PROVEEDOR[/]: [cyan]{provider_label}[/] | [white]{model_label}[/]\n"
            f"🧠 [bold]MEMORIA[/]:    SQLite ([white]{db_size_kb} KB[/])\n"
            f"🔌 [bold]PLUGINS[/]:    [cyan]{plugins_count}[/] Herramientas Activas\n"
            f"⚡ [bold]PRM SCORER[/]: {prm_status}"
        )
        
        if is_local:
            diag_text += f"\n🔒 [bold]CONTEXTO[/]:   [green]Local (Ventana 10 msg - Ultra Velocidad ⚡)[/]"
        else:
            diag_text += f"\n☁️ [bold]CONTEXTO[/]:   [blue]Nube (Ventana 100 msg - Memoria Profunda ☁️)[/]"
            
        self.console.print(Panel(diag_text, border_style="blue", expand=False))
        self.console.print(f"\n{Colors.CYAN}{'─' * 40}{Colors.END}\n")

    def _check_startup_connection(self):
        """Verifica la conexión con el proveedor al arrancar y avisa si falla."""
        try:
            if not asyncio.run(self.brain.check_connection()):
                self.console.print(f"[bold yellow][!] Advertencia: No se pudo conectar con el proveedor seleccionado.[/]")
                self.console.print(f"[bold yellow]    Asegurate de que el servidor local o tu API key esten configurados.[/]\n")
        except Exception as e:
            self.console.print(f"[bold red][!] Error crítico verificando conexión: {e}[/]")

    def _input_loop(self, is_local: bool):
        """Loop principal de input del CLI con interfaz enriquecida."""
        prompt_text = "Anti@Local" if is_local else "Anti@Cloud"
        prompt_color = "green" if is_local else "blue"
        
        self.console.print("\n[bold magenta]Bienvenido al núcleo de Anti-Agent. Escribe [bold cyan]'help'[ /bold cyan] para ver comandos.[/bold magenta]")
        
        while self.is_running:
            try:
                # Prompt estilizado
                user_input = self.console.input(f"[{prompt_color} bold]❯ {prompt_text}[/]")
                user_input = user_input.strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ["exit", "quit"]:
                    self.is_running = False
                    self.console.print(f"\n[bold blue][*] Apagando sistemas... ¡Hasta pronto! 🚀[/]")
                    break
                
                # Procesamiento con spinner de carga
                with self.console.status(f"[bold yellow]Procesando...[/]", spinner="dots") as status:
                    result = asyncio.run(self.handle_command(user_input))
                
                if result:
                    if isinstance(result, dict) and "response" in result:
                        # Renderizar respuesta en un panel elegante
                        formatted_response = self.render_markdown(result['response'])
                        self.console.print(Panel(formatted_response, title="[bold cyan]Anti[/]", border_style="blue"))
                    else:
                        formatted_result = self.render_markdown(str(result))
                        self.console.print(Panel(formatted_result, title="[bold cyan]Anti[/]", border_style="blue"))
                        
            except KeyboardInterrupt:
                self.console.print(f"\n[bold yellow][!] Interrumpido por el usuario.[/]")
                self.is_running = False
                break
            except EOFError:
                self.console.print(f"\n[bold yellow][!] EOF recibido. Saliendo...[/]")
                self.is_running = False
                break
            except Exception as e:
                app_logger.exception(f"Error en CLI loop")
                self.console.print(f"\n[bold red][!] Error: {e}[/]")

    # --- Command Handler ---

    async def handle_command(self, cmd, image_data=None):
        cmd_lower = cmd.lower().strip()

        if cmd_lower == "help":
            return self._show_help()
        elif cmd_lower == "status":
            return await self._show_status()
        elif cmd_lower == "metrics":
            # Return current metrics snapshot
            return metrics.get_metrics()
        elif cmd_lower == "reasoner":
            return self._toggle_reasoner()
        elif cmd_lower == "reflect":
            findings = await self._reflect()
            return f"Reflexion completada.\n\n{findings}"
        elif cmd_lower == "compact":
            await self._compact_memory()
            return "Memoria compactada."
        elif cmd_lower == "forget":
            self.memory.forget()
            print(f"{Colors.RED}[!] Memoria de patrones borrada.{Colors.END}")
            return "Memoria borrada."
        elif cmd_lower == "plugins":
            return self._list_plugins()
        elif cmd_lower == "memories":
            return self._show_memories()
        elif cmd_lower == "engra":
            return self._list_engrams()
        elif cmd_lower.startswith("search "):
            query = cmd[7:].strip()
            return await self._force_search(query)
        elif cmd_lower == "consolidate":
            stats = await self.consolidator.run_maintenance()
            return f"Consolidación finalizada: {stats['deleted_decay']} purgados, {stats['consolidated_engrams']} sintetizados."
        elif cmd_lower == "renew" or cmd_lower == "/r":
            return await self._renew_system()
        
        # --- MCP Commands (Phase 3.2) ---
        elif cmd_lower.startswith("mcp "):
            return self._handle_mcp_command(cmd[4:].strip())
        
        else:
            return await self._process(cmd, image_data=image_data)


    # --- Core Processing ---

    async def _process(self, user_msg, image_data=None):
        user_text = user_msg if isinstance(user_msg, str) else str(user_msg)
        
        # 1. Build System Prompt
        system_prompt = self._build_system_prompt(user_text)
        
        # 2. Build conversation thread
        messages = [{"role": "system", "content": system_prompt}]
        for msg in self.history:
            if isinstance(msg["content"], list):
                text = next((item["text"] for item in msg["content"] if item["type"] == "text"), "Imagen previa")
                messages.append({"role": msg["role"], "content": text})
            else:
                messages.append(msg)
        
        if image_data:
            print(f"{Colors.YELLOW}[i] Imagen recibida para analisis.{Colors.END}")
            user_content = [
                {"type": "text", "text": user_msg if user_msg else "Analiza esta imagen."},
                {"type": "image_url", "image_url": {"url": image_data}}
            ]
        else:
            user_content = user_msg
            
        messages.append({"role": "user", "content": user_content})
        
        # 3. Initial Chat Inference
        start_timestamp = time.time()
        metrics.record_inference(model=self.brain.model, ttft_ms=0, tokens_generated=0, duration_seconds=0)
        
        try:
            response, usage = await asyncio.wait_for(self.brain.chat(messages), timeout=120)
            metrics.record_ttft(start_timestamp)
            completion_tokens = usage.get('completion_tokens', 0)
            duration = usage.get('duration') if usage.get('duration') is not None else usage.get('time', 0)
            metrics.record_token_generation(completion_tokens, duration)
            self.brain.record_usage(usage)
            self.context_mgr.token_count = usage.get("prompt_tokens", 0)
        except Exception as e:
            app_logger.exception(f"Chat inference failed")
            return {
                "response": f"Error en inferencia: {e}",
                "steps": [],
                "sources": {},
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "duration": 0, "tps": 0},
                "score": 0.0
            }

        if isinstance(response, (list, tuple)):
            response_str = response[0] if len(response) > 0 else ""
        else:
            response_str = str(response)
            
        if "Error conectando con LM Studio" in response_str:
            app_logger.error(f"LM Studio connection error: {response_str}")
            print(f"{Colors.RED}[!] {response_str}{Colors.END}")
            return {
                "response": f"No pude procesar tu solicitud. Error de LM Studio: {response_str}",
                "steps": [],
                "sources": {},
                "usage": usage if 'usage' in locals() else {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "duration": 0, "tps": 0},
                "score": 0.0
            }

        response = response_str.replace("<thought>", "").replace("</thought>", "").strip()

        # 4. ReAct Tool Loop
        final_response, execution_steps, extracted_sources, final_usage = await self._run_tool_loop(messages, response, user_text)
        
        # 5. Evaluation & Refinement
        tool_step = len(execution_steps)
        final_response, score, is_success, votes = await self._evaluate_response(final_response, user_text, tool_step)
        
        # 6. Update History & Stats
        self._update_history(user_msg, final_response, is_success, score, votes)
        
        # Auto-maintenance
        self.task_counter += 1
        if self.task_counter >= 10:
            await self._reflect()
            self.task_counter = 0
        
        await self._check_integrity(final_usage.get("prompt_tokens", 0) if final_usage else 0)
        
        return {
            "response": final_response,
            "steps": execution_steps,
            "sources": extracted_sources,
            "usage": final_usage if final_usage else usage,
            "score": score
        }

    def _build_system_prompt(self, user_text):
        """Builds the system prompt including omni-context and optional document overrides."""
        name = self.config.get("agent_name", "Anti")
        personality = self.config.get("personality", "Sos un agente autonomo avanzado.")
        
        # LECTURA MODE: detect @mentions to load a local document as exclusive context
        reading_context = None
        locked_to_doc = False
        at_mentions = re.findall(r'@(\S+)', user_text)
        if at_mentions:
            lectura_dir = os.path.join(self.base_dir, "lectura")
            workspace_dir = os.path.join(self.base_dir, "workspace")
            loaded_docs = []
            for mention in at_mentions:
                # Search in lectura/ first, then workspace/
                for search_dir in [lectura_dir, workspace_dir]:
                    doc_path = os.path.join(search_dir, os.path.basename(mention))
                    if os.path.exists(doc_path):
                        try:
                            with open(doc_path, "r", encoding="utf-8") as f:
                                content = f.read()
                            loaded_docs.append(f"--- DOCUMENTO: {mention} ---\n{content}\n--- FIN DOCUMENTO ---")
                            print(f"{Colors.GREEN}[+] Documento @{mention} cargado como referencia exclusiva.{Colors.END}")
                        except Exception as e:
                            loaded_docs.append(f"[Error leyendo {mention}: {e}]")
                        break
            if loaded_docs:
                reading_context = "\n\n".join(loaded_docs)
                locked_to_doc = True

        # OMNISCIENT HIPPOCAMPUS: Retrieve all latent memory automatically
        omni_context = self.memory.retrieve_omni_context(user_text)

        # ANTI-MEMORY-CORE: Cargar boot_payload.json generado por Go
        boot_payload = {}
        boot_path = os.path.join(self.base_dir, "memory", "boot_payload.json")
        if os.path.exists(boot_path):
            try:
                with open(boot_path, "r", encoding="utf-8") as f:
                    boot_payload = json.load(f)
            except Exception as e:
                print(f"[MemoryCore] Error cargando boot_payload.json: {e}")
        
        dynamic_system_directives = ""
        core_prompt = boot_payload.get("core_prompt")
        id_proyecto = boot_payload.get("id_proyecto", "Anti_Core")
        if core_prompt:
            dynamic_system_directives += f"\n\n[CORE PROJECT DIRECTIVES: {id_proyecto}]\n{core_prompt}"
        
        engrams = boot_payload.get("engrams_imported")
        if engrams:
            dynamic_system_directives += "\n\n[EVOLUTIONARY MEMORY - DISTILLED ENGRAMS]"
            for eng in engrams:
                dynamic_system_directives += f"\n\n{eng}"

        # Combine with omni_context
        if dynamic_system_directives:
            omni_context = dynamic_system_directives + "\n\n[OMNI_CONTEXT_ARCHIVE]\n" + omni_context

        system_prompt = build_system_prompt(
            name=name,
            personality=personality,
            omni_context=omni_context,
            dynamic_tools=self.plugin_manager.get_tool_descriptions()
        )

        # 5. DYNAMIC SKILL TRIGGER SYSTEM (MIDDLEWARE)
        skills = boot_payload.get("skills")
        if skills:
            active_overrides = []
            for skill in skills:
                kw = skill.get("trigger_keyword")
                if kw:
                    # Match trigger_keyword in user input (case-insensitive)
                    if re.search(rf"\b{re.escape(kw)}\b", user_text, re.IGNORECASE):
                        active_overrides.append(
                            f"[SYSTEM OVERRIDE: SKILL ACTIVE]\n"
                            f"Skill: {skill.get('nombre_skill', kw)}\n"
                            f"{skill.get('instrucciones_markdown', '')}\n"
                            f"[/SYSTEM OVERRIDE]"
                        )
            if active_overrides:
                system_prompt += "\n\n" + "\n\n".join(active_overrides)

        # If locked to a document, inject a hard override into the system prompt
        if locked_to_doc and reading_context:
            doc_override = (
                "\n\n=== MODO LECTURA ESTRICTO ACTIVADO ===\n"
                "El usuario ha proveído los siguientes documentos como ÚNICA fuente de información.\n"
                "PROHIBICIÓN ABSOLUTA: NO uses herramientas de búsqueda web (SEARCH, FETCH, RESEARCH).\n"
                "Tu respuesta DEBE basarse EXCLUSIVAMENTE en el contenido de estos documentos.\n"
                "Si la información no está en los documentos, dilo directamente.\n\n"
                + reading_context
            )
            system_prompt = system_prompt + doc_override
            
        return system_prompt

    async def _run_tool_loop(self, messages, initial_response, user_msg):
        """Handles the ReAct tool loop, returning final response, steps, and sources."""
        MAX_TOOL_STEPS = 10
        tool_step = 0
        execution_steps = []
        extracted_sources = {}
        response = initial_response
        
        while tool_step < MAX_TOOL_STEPS:
            tool_triggered = False
            tool_context = None
            current_step = {"step": tool_step + 1, "tool": None, "query": None, "result_summary": None}

            # Detect which tool the model wants to use (via brain.process_response)
            is_tool, valid_calls, clean_response = self.brain.process_response(response)
            tool_name = valid_calls[0][0] if valid_calls else None
            tool_args = valid_calls[0][1] if valid_calls else None
            if is_tool and tool_name in self.plugin_manager.tools:
                raw_args = json.dumps(tool_args) if isinstance(tool_args, dict) else str(tool_args)
                print(f"{Colors.YELLOW}[*] [{tool_step+1}/{MAX_TOOL_STEPS}] {tool_name}: {raw_args[:50]}...{Colors.END}")
                
                # Execute dynamically
                try:
                    result = await self.plugin_manager.execute_tool(tool_name, raw_args)
                    try:
                        json.loads(result)
                        metrics.record_parse_success(True)
                    except Exception as e:
                        app_logger.debug(f"Result parsing failed: {e}")
                        metrics.record_parse_success(False)
                except Exception as e:
                    app_logger.exception(f"Tool execution failed: {tool_name}")
                    result = f"[ERROR] La herramienta {tool_name} falló: {e}"
                
                tool_triggered = True
                current_step.update({"tool": tool_name, "query": raw_args, "result_summary": str(result)[:200] + "..."})
                
                # Extract URLs for UI if present
                if isinstance(result, str):
                    found_urls = re.findall(r'URL: (https?://[^\s\n\]]+)', result)
                    for url in found_urls:
                        if url not in extracted_sources.values():
                            extracted_sources[len(extracted_sources) + 1] = url
                
                # CHAINING: if SEARCH ran, auto-execute WEB_READ on each result URL
                if tool_name == "SEARCH" and isinstance(result, str):
                    found_urls = re.findall(r'URL: (https?://[^\s\n\]]+)', result)
                    web_read_results = []
                    for i, url in enumerate(found_urls[:3]):
                        print(f"{Colors.GREEN}[*] Auto-WEB_READ [{i+1}/{min(len(found_urls),3)}]: {url[:60]}...{Colors.END}")
                        web_content = await self.plugin_manager.execute_tool("WEB_READ", url)
                        web_read_results.append(f"\n--- WEB_READ [{i+1}] {url} ---\n{web_content}")
                        current_step.setdefault("chained_reads", []).append(url[:80])
                    if web_read_results:
                        result += "\n\n" + "".join(web_read_results)
                
                tool_context = f"[RESULTADO {tool_name}]\n{result}\n\nContinua con la tarea. Podes usar otra herramienta si necesitas mas informacion, o entrega la respuesta final."
            elif is_tool:
                tool_triggered = True
                tool_context = f"[ERROR] La herramienta {tool_name} no existe. Revisa las herramientas disponibles en tus instrucciones."
            
            if not tool_triggered:
                # No tool called → final response
                break

            execution_steps.append(current_step)
            
            # Feed tool result back to the model
            messages.append({"role": "assistant", "content": response})
            messages.append({"role": "user", "content": tool_context})
            print(f"{Colors.CYAN}[*] Procesando resultado de herramienta...{Colors.END}")
            try:
                response, usage = await asyncio.wait_for(self.brain.chat(messages), timeout=120)
                self.brain.record_usage(usage)
                self.context_mgr.token_count = usage.get("prompt_tokens", 0)
                response = response.replace("<thought>", "").replace("</thought>", "").strip()
            except Exception as e:
                app_logger.exception(f"Chat inference failed in tool loop")
                response += f"\n\n[Error al procesar herramienta: {e}]"
                break
            tool_step += 1
            
        return response, execution_steps, extracted_sources, usage if 'usage' in locals() else None


    async def _evaluate_response(self, response, user_text, tool_step):
        """Evaluates response quality using PRM Scorer and optionally refines."""
        try:
            result = await self.scorer.evaluate(
                response=response,
                instruction=user_text,
                turn_num=tool_step,
            )
            score = result.get("score")
            votes = result.get("votes", [])
            is_success = score is not None and score > 0
            return response, score, is_success, votes
        except Exception as e:
            app_logger.warning(f"PRM evaluation failed: {e}")
            return response, None, False, []

    # --- Reasoner ---

    def _toggle_reasoner(self):
        self.reasoner_mode = not self.reasoner_mode
        status = "ACTIVADO" if self.reasoner_mode else "DESACTIVADO"
        msg = f"Modo Reasoner: {status}"
        print(f"{Colors.YELLOW}[*] {msg}{Colors.END}")
        return msg

    async def _renew_system(self):
        """Reinicia el servidor y refresca el estado del sistema."""
        print(f"{Colors.BLUE}[*] Iniciando ciclo de renovación...{Colors.END}")
        try:
            # Cleanup zombies before starting new ones
            self._cleanup_zombies()
            
            # Matar servidor existente
            pattern = re.escape(os.path.join(self.base_dir, 'server.py'))
            subprocess.run(["pkill", "-f", pattern], capture_output=True)
            print(f"{Colors.BLUE}[*] Servidores previos detenidos.{Colors.END}")
            
            # Iniciar nuevo servidor en segundo plano
            python_exe = "python3"
            venv_python = os.path.join(self.base_dir, "venv/bin/python3")
            if os.path.exists(venv_python):
                python_exe = venv_python
            
            server_script = os.path.join(self.base_dir, "server.py")
            proc = subprocess.Popen(
                [python_exe, server_script], 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                cwd=self.base_dir
            )
            # Store process to avoid zombies
            self.server_proc = proc
            print(f"{Colors.GREEN}[+] Nuevo servidor iniciado con el código actualizado.{Colors.END}")
            
            # Pausa y health check
            await asyncio.sleep(1)
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    health_res = await client.get("http://127.0.0.1:8000/health", timeout=2)
                    if health_res.status_code == 200:
                        return "✅ Sistema renovado. El dashboard y el servidor ahora corren con la última versión."
                    else:
                        return f"⚠️ Servidor iniciado pero salud no confirmada (Status: {health_res.status_code})."
            except Exception as e:
                return f"⚠️ Servidor iniciado pero no se pudo contactar el endpoint de salud: {e}"
                
        except Exception as e:
            return f"❌ Error al renovar: {e}"

    def _cleanup_zombies(self):
        """Checks and cleans up the server process if it's a zombie."""
        if hasattr(self, 'server_proc') and self.server_proc:
            if self.server_proc.poll() is not None:
                app_logger.debug("Server process was already dead, cleaned up.")
            else:
                # Process is still running, nothing to clean specifically unless we want to kill it
                pass

    async def _force_search(self, query):
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

        print(f"{Colors.YELLOW}[*] Forzando búsqueda web ({time_period or 'todo'}): {query}...{Colors.END}")
        search_results = duckduckgo_search(query, time_period=time_period)
        
        context = f"El usuario forzo una busqueda web para: {query}\n\nResultados:\n{search_results}\n\nResponde en base a esto."
        return await self._process(context)

    async def _admin_command(self, cmd):
        """Admin simplificado: solo delete y move para manejo de archivos."""
        print(f"{Colors.RED}[!] Modo Admin activado.{Colors.END}")
        parts = cmd.strip().split(maxsplit=2)
        
        if len(parts) < 3:
            return (
                "ADMIN — Comandos disponibles:\n"
                "  admin delete <nombre_archivo>   — Elimina un archivo del workspace, engrams o lectura\n"
                "  admin move <archivo> <destino>  — Mueve un archivo a workspace, engrams o lectura"
            )

        action = parts[1].lower()

        # --- DELETE ---
        if action == "delete":
            target = parts[2].strip()
            safe_name = os.path.basename(target)
            search_dirs = [
                ("workspace",       os.path.join(self.base_dir, "workspace")),
                ("engrams",         os.path.join(self.base_dir, "memory", "engrams")),
                ("lectura",         os.path.join(self.base_dir, "lectura")),
            ]
            for label, d in search_dirs:
                path = os.path.join(d, safe_name)
                if os.path.exists(path) and os.path.isfile(path):
                    os.remove(path)
                    print(f"{Colors.RED}[!] Eliminado: {path}{Colors.END}")
                    return f"[ADMIN] Archivo '{safe_name}' eliminado de {label}/."
            return f"[ADMIN] No encontré '{safe_name}' en workspace, engrams ni lectura."

        # --- MOVE ---
        elif action == "move":
            if len(parts) < 4:
                # re-split: 'admin move archivo destino'
                sub = cmd.strip().split(maxsplit=3)
                if len(sub) < 4:
                    return "[ADMIN] Uso: admin move <archivo> <destino> (destino: workspace | engrams | lectura)"
                parts = sub

            src_name = os.path.basename(parts[2].strip())
            dst_label = parts[3].strip().lower().rstrip("/")

            dest_map = {
                "workspace":  os.path.join(self.base_dir, "workspace"),
                "engrams":    os.path.join(self.base_dir, "memory", "engrams"),
                "lectura":    os.path.join(self.base_dir, "lectura"),
            }
            if dst_label not in dest_map:
                return f"[ADMIN] Destino inválido '{dst_label}'. Usa: workspace | engrams | lectura"

            src_dirs = list(dest_map.values())
            src_path = None
            for d in src_dirs:
                candidate = os.path.join(d, src_name)
                if os.path.exists(candidate):
                    src_path = candidate
                    break

            if not src_path:
                return f"[ADMIN] No encontré '{src_name}' en ninguna carpeta."

            dst_path = os.path.join(dest_map[dst_label], src_name)
            shutil.move(src_path, dst_path)
            print(f"{Colors.GREEN}[+] Movido: {src_path} -> {dst_path}{Colors.END}")
            return f"[ADMIN] '{src_name}' movido a {dst_label}/."

        else:
            return f"[ADMIN] Acción '{action}' no reconocida. Usa: delete | move"

    # --- Evolution & Reflection ---

    async def _reflect(self):
        print(f"{Colors.YELLOW}[*] Iniciando evolucion autonoma profunda (Dual)...{Colors.END}")
        logs = self.memory.get_recent_logs(50)
        
        # 1. Pase Factual: Extraer Engrams de los exitos
        print(f"{Colors.YELLOW}[*] Fase 1: Extrayendo conocimiento factual (Engrams)...{Colors.END}")
        try:
            # PRM scorer / evolver might have asyncio inside or be async already
            new_engrams = await self.evolver.extract_engrams(logs)
            for e in new_engrams:
                self.memory.save_engram(e.get("topic", "tema-desconocido"), e.get("content", ""))
                print(f"{Colors.GREEN}[+] Engram memorizado: {e.get('topic')}{Colors.END}")
        except Exception as e:
            app_logger.exception("Error in Engram extraction")
            print(f"{Colors.RED}[!] Error en extraccion de Engrams: {e}{Colors.END}")

        # 2. Pase Conductual: Refinar Skills
        print(f"{Colors.YELLOW}[*] Fase 2: Analizando {len(logs)} experiencias para destilar mejores practicas...{Colors.END}")
        try:
            new_skills = await self.evolver.evolve(logs, self.memory.skills.skills)
        except Exception as e:
            app_logger.exception("Error in Skill Evolver")
            print(f"{Colors.RED}[!] Error en Evolver (Skills): {e}{Colors.END}")
            return "Error en evolucion de habilidades."

        if not new_skills:
            print(f"{Colors.YELLOW}[i] El sistema considera que las reglas actuales son optimas.{Colors.END}")
            return "Evolucion completada sin nuevas reglas de comportamiento."

        for skill in new_skills:
            self.memory.skills.add_skill(
                name=skill.get("name"),
                description=skill.get("description"),
                content=skill.get("content"),
                category=skill.get("category", "forced-evolution")
            )
            print(f"{Colors.GREEN}[+] Evolucion aplicada: {skill.get('name')}{Colors.END}")

        return f"Evolucion Dual completada. Nuevos Engrams memorizados y {len(new_skills)} nuevas directivas añadidas."

    async def _compact_memory(self):
        print(f"{Colors.BLUE}[*] Compactando memoria...{Colors.END}")
        patterns = self.memory.load_patterns()
        if not patterns.strip():
            print(f"{Colors.YELLOW}[i] Memoria vacia, nada que compactar.{Colors.END}")
            return

        prompt = COMPACT_PROMPT.format(patterns=patterns[:4000])
        compacted, _ = await self.brain.chat([{"role": "user", "content": prompt}])
        self.memory.save_pattern(compacted)
        print(f"{Colors.GREEN}[+] Memoria compactada.{Colors.END}")

    # --- UI Commands ---

    def _handle_mcp_command(self, args):
        """CLI handler for MCP (Model Capability Protocol) commands."""
        parts = args.strip().split(maxsplit=1)
        if not parts:
            return "MCP — Uso: mcp <list|install|remove|help> [id]"
        
        action = parts[0].lower()
        mcp_id = parts[1].strip() if len(parts) > 1 else ""
        
        if action == "list":
            return self._mcp_list()
        elif action == "install":
            if not mcp_id:
                return "MCP install — Uso: mcp install <id>"
            return self._mcp_install(mcp_id)
        elif action == "remove":
            if not mcp_id:
                return "MCP remove — Uso: mcp remove <id>"
            return self._mcp_remove(mcp_id)
        elif action == "help":
            if not mcp_id:
                return "MCP help — Uso: mcp help <id>"
            return self._mcp_help(mcp_id)
        else:
            return f"MCP: comando '{action}' no reconocido. Usa: list, install, remove, help"

    def _mcp_list(self):
        """Lista MCPs instalados y disponibles."""
        skills_dir = os.path.join(self.base_dir, "memory", "skills")
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
                    # Parse frontmatter
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

    def _mcp_install(self, mcp_id):
        """Instala un MCP (download + save)."""
        # Sanitize ID for folder name
        safe_id = re.sub(r'[^a-zA-Z0-9_-]', '', mcp_id.lower()) or "unnamed-mcp"
        skills_dir = os.path.join(self.base_dir, "memory", "skills")
        
        # Check if already exists
        existing_path = os.path.join(skills_dir, safe_id, "SKILL.md")
        if os.path.exists(existing_path):
            return f"MCP '{mcp_id}' ya está instalado."
        
        # Create MCP directory with template SKILL.md
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
        
        # Reload skills if available
        if hasattr(self.memory, "skills"):
            self.memory.skills.reload()
        
        return f"MCP '{mcp_id}' instalado correctamente en memory/skills/{safe_id}/"

    def _mcp_remove(self, mcp_id):
        """Remueve un MCP."""
        safe_id = re.sub(r'[^a-zA-Z0-9_-]', '', mcp_id.lower()) or "unnamed-mcp"
        if not safe_id:
            return "[ERROR] Invalid MCP ID"
        skills_dir = os.path.join(self.base_dir, "memory", "skills")
        mcp_dir = os.path.join(skills_dir, safe_id)
        
        if not os.path.exists(mcp_dir):
            return f"MCP '{mcp_id}' no encontrado."
        
        # Log directory size before removal
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
        
        # Reload skills if available
        if hasattr(self.memory, "skills"):
            self.memory.skills.reload()
        
        return f"MCP '{mcp_id}' removido correctamente."

    def _mcp_help(self, mcp_id):
        """Muestra ayuda de un MCP."""
        safe_id = re.sub(r'[^a-zA-Z0-9_-]', '-', mcp_id.lower())
        skills_dir = os.path.join(self.base_dir, "memory", "skills")
        skill_path = os.path.join(skills_dir, safe_id, "SKILL.md")
        
        if not os.path.exists(skill_path):
            return f"MCP '{mcp_id}' no encontrado."
        
        try:
            with open(skill_path, "r", encoding="utf-8") as f:
                content = f.read()
            return f"=== MCP: {safe_id} ===\n\n{content}"
        except Exception as e:
            return f"Error leyendo MCP '{mcp_id}': {e}"

    def _list_plugins(self):
        title = f"\n{Colors.CYAN}{Colors.BOLD}🔌 PLUGINS & HERRAMIENTAS ACTIVAS EN ANTI{Colors.END}\n"
        lines = [title]
        if hasattr(self, "plugin_manager") and self.plugin_manager and self.plugin_manager.tools:
            for name, tool in self.plugin_manager.tools.items():
                desc = tool.get("description", "Sin descripción")
                lines.append(f"  {Colors.GREEN}{Colors.BOLD}• {name}{Colors.END}: {desc}")
        else:
            lines.append(f"  {Colors.YELLOW}No se encontraron plugins dinámicos cargados.{Colors.END}")
        lines.append("")
        result = "\n".join(lines)
        print(result)
        return result

    def _show_help(self):
        help_text = """
ANTI-AGENT — COMANDOS

  [Chat]
    Escribi cualquier pregunta y el agente responde.
    search <query>  Fuerza una busqueda web inmediata.

  [Plugins & Herramientas]
    plugins         Lista todos los plugins y herramientas cargadas en Anti.

  [MCP - Model Capability Protocol]
    mcp list          Lista todos los MCPs instalados
    mcp install <id> Instala un nuevo MCP
    mcp remove <id>  Remueve un MCP instalado
    mcp help <id>    Muestra ayuda de un MCP

  [Sistema]
    reasoner    Activa/desactiva auto-critica de respuestas.
    reflect     Analiza experiencias pasadas y genera reglas (evolución).
    memories    Muestra un resumen de la memoria del agente (logs, patrones, engrams).
    engra       Lista todos los engrams (conocimiento persistente) con resumen.
    compact     Comprime la memoria de patrones.
    consolidate Inicia el mantenimiento autónomo y purga de datos.
    renew / /r  Reinicia el servidor y aplica las últimas actualizaciones.
    forget      Borra toda la memoria.
    status      Estado del sistema.
    exit/quit   Apagar.
"""
        print(f"{Colors.CYAN}{help_text}{Colors.END}")
        return help_text

    def _show_memories(self):
        """Resumen de la memoria del agente.
        Incluye cantidad de logs, patrones guardados y engrams.
        """
        logs = self.memory.get_recent_logs(5)
        patterns = self.memory.load_patterns()
        engrams_count = self.memory.count_engrams()
        summary = f"""
MEMORIA DEL AGENTE
  Logs recientes: {len(logs)}
  Patrones guardados: {'Sí' if patterns.strip() else 'No'}
  Engrams almacenados: {engrams_count}
"""
        print(f"{Colors.GREEN}{summary}{Colors.END}")
        return summary

    def _list_engrams(self):
        """Lista todos los engrams con un mini resumen."""
        engrams_path = self.memory.engrams_path
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
                logger.warning(f"[Agent] Error reading engram {filename}: {e}")
        
        res = "\n".join(output)
        print(f"{Colors.GREEN}{res}{Colors.END}")
        return res

    async def _show_status(self):
        connected = await self.brain.check_connection()
        conn_str = "Conectado" if connected else "Desconectado"
        logs = self.memory.get_recent_logs(1000)
        reasoner_status = "ON" if self.reasoner_mode else "OFF"

        # v0.6 Sentinel Metrics
        ctx_stats = self.context_mgr.get_advanced_stats()
        load_percent = self.context_mgr.usage_percent
        integrity_level = self.context_mgr.get_load_level()
        
        status_text = f"""
ESTADO DEL SISTEMA (Sentinel v1.3 Active)
  LM Studio:       {conn_str}
  Modo Reasoner:   {reasoner_status}
  Skills:          {len(self.memory.skills.skills)} activas
  Experiencias:    {len(logs)} logs registrados
  Workspace:       {self.memory.count_workspace_files()} archivos
  Engrams:         {self.memory.count_engrams()} memorias
  
  [Context Integrity]
  Carga Actual:    {load_percent}% ({integrity_level})
  Eficiencia:      {ctx_stats['efficiency_score']}%
  Tokens Salvados: {self.context_mgr.tokens_saved}
"""
        print(status_text)
        return status_text

    async def _check_integrity(self, current_prompt_tokens=0):
        """
        Trigger unificado basado en Matriz de Integridad v0.5 (Anti Edition).
        """
        # 0. Actualizar contador de tokens en el manager
        if current_prompt_tokens > 0:
            self.context_mgr.token_count = current_prompt_tokens
            
        # 1. Sync dynamic context
        await self.brain.sync_model_context()
        context_info = await self.brain.get_context_info()
        model_context = context_info.get("max", 32000)
        
        # Re-inicializar si cambió el context del modelo
        if self.context_mgr.model_context_length != model_context:
            self.context_mgr.update_context_length(model_context)
        
        # Sync scorer model
        self.scorer.prm_model = self.brain.model
        
        # 2. Get load level
        usage_percent = self.context_mgr.usage_percent
        level = self.context_mgr.get_load_level()
        action = self.context_mgr.get_integrity_action()
        
        # 3. Execute action
        if level == "warning":
            removed = self.context_mgr.deduplicate()
            if removed > 0:
                print(f"{Colors.YELLOW}[*] Anti-Deduplication: {removed} mensajes redundantes eliminados.{Colors.END}")
            
        elif level == "critical" or level == "overflow":
            print(f"{Colors.RED}[!] Anti-Alert ({level}): {usage_percent}%. Limpieza Sentinel...{Colors.END}")
            self.context_mgr.deduplicate()
            await self.consolidator.run_maintenance()
            await self._compact_memory()
            return

        # 4. Memoria basada en engrams
        engrams_count = self.memory.count_engrams()
        skills_count = len(self.memory.skills.skills)
        total = engrams_count + skills_count
        thresholds = [20] + list(range(50, 550, 50))
        
        current_threshold = 0
        for t in thresholds:
            if total >= t: current_threshold = t
            else: break
        
        if current_threshold > self.last_maintenance_count:
            print(f"{Colors.CYAN}[*] Anti-Memory Threshold ({total}). Consolidando...{Colors.END}")
            await self.consolidator.run_maintenance()
            self.last_maintenance_count = current_threshold

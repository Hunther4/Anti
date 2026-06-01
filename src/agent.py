"""
AntiAgent — Core orchestrator (v1.6 Quantum).

Slimmed-down version: delegates to renderer, prompt_builder,
tool_orchestrator, and command_handler modules.
"""

import os
import json
import re
import asyncio
import logging
import subprocess
import time
import uuid

from rich.console import Console
from rich.panel import Panel

from src.logger import AppLogger, Colors, set_request_id
from src.brain import Brain
from src.memory import MemoryManager
from src.context_manager import ContextManager
from src.scorer import PRMScorer
from src.evolver import SkillEvolver
from src.consolidator import MemoryConsolidator
from src import metrics

from src.renderer import render_markdown, display_banner
from src.prompt_builder import build_agent_prompt
from src.tool_orchestrator import run_tool_loop
from src import command_handler

logger = logging.getLogger(__name__)
app_logger = AppLogger(__name__)


class AntiAgent:
    DEFAULT_LM_URL = "http://127.0.0.1:1234/v1"

    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.console = Console()

        # Local-First config
        self.local_config_path = os.path.join(self.base_dir, "config.local.json")
        self.default_config_path = os.path.join(self.base_dir, "config.json")
        self.config = self._load_config()

        # Provider initialization
        from src.providers import create_provider
        provider_type = self.config.get("provider", "auto")
        if provider_type == "auto":
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
                logger.warning(f"Auto-deteccion fallo: {e}. Usando LM Studio por defecto.")
                self.brain = create_provider(
                    "lmstudio",
                    base_url=self.config.get("lm_studio_url", self.DEFAULT_LM_URL),
                    model=self.config.get("model")
                )
        else:
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

        self.context_mgr = ContextManager(model_context_length=32000)
        self.is_running = True
        self.task_counter = 0
        self.history = []
        self.reasoner_mode = False

        url = getattr(self.brain, 'base_url', self.config.get("lm_studio_url", self.DEFAULT_LM_URL))
        self.scorer = PRMScorer(prm_url=url, prm_model=self.brain.model)
        self.evolver = SkillEvolver(base_url=url, model="local-model")

        from src.plugin_manager import PluginManager
        self.plugin_manager = PluginManager(plugins_dir=os.path.join(self.base_dir, "src/plugins"))
        self.consolidator = MemoryConsolidator(self.memory, self.evolver)
        self.last_maintenance_count = 0

    def _load_config(self):
        for path in (self.local_config_path, self.default_config_path):
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
        raise FileNotFoundError(
            "Configuration file not found. Please copy config.json.example to "
            "config.local.json and fill in your keys."
        )

    async def close(self):
        if hasattr(self, 'brain') and self.brain:
            if hasattr(self.brain, 'close'):
                await self.brain.close()
        app_logger.info("AntiAgent resources closed successfully.")

    # --- Delegated: Rendering ---

    def render_markdown(self, text: str) -> str:
        return render_markdown(text)

    # --- Delegated: Commands ---

    async def handle_command(self, cmd, image_data=None):
        return await command_handler.handle_command(cmd, self, image_data=image_data)

    # --- Core Processing Pipeline ---

    async def _process(self, user_msg, image_data=None, _depth=0):
        # Guard: prevent stack overflow from recursive refinement
        if _depth > 3:
            logger.warning("[Agent] Max refinement depth reached, returning as-is")
            return {"response": str(user_msg), "steps": [], "sources": {}, "usage": {}, "score": 0.0}

        user_text = user_msg if isinstance(user_msg, str) else str(user_msg)

        # Generate correlation ID for this request
        rid = uuid.uuid4().hex[:12]
        set_request_id(rid)

        # 1. Build System Prompt
        system_prompt = build_agent_prompt(
            user_text=user_text,
            config=self.config,
            memory=self.memory,
            plugin_manager=self.plugin_manager,
            base_dir=self.base_dir,
        )

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
                {"type": "text", "text": user_text if user_text else "Analiza esta imagen."},
                {"type": "image_url", "image_url": {"url": image_data}}
            ]
        else:
            user_content = user_msg

        messages.append({"role": "user", "content": user_content})

        # 3. Initial Chat Inference
        start_timestamp = time.time()

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
                "steps": [], "sources": {},
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "duration": 0, "tps": 0},
                "score": 0.0
            }

        if isinstance(response, (list, tuple)):
            response_str = response[0] if len(response) > 0 else ""
        else:
            response_str = str(response)

        if response_str.startswith("Error") and ("conectando" in response_str or "connecting" in response_str or "Error en" in response_str):
            app_logger.error(f"Provider connection error: {response_str}")
            print(f"{Colors.RED}[!] {response_str}{Colors.END}")
            return {
                "response": f"No pude procesar tu solicitud. Error de conexion: {response_str}",
                "steps": [], "sources": {},
                "usage": usage if 'usage' in locals() else {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "duration": 0, "tps": 0},
                "score": 0.0
            }

        response = response_str.replace("<thought>", "").replace("</thought>", "").strip()

        # 4. ReAct Tool Loop (delegated)
        final_response, execution_steps, extracted_sources, final_usage = await run_tool_loop(
            messages=messages,
            initial_response=response,
            user_msg=user_text,
            brain=self.brain,
            plugin_manager=self.plugin_manager,
            context_mgr=self.context_mgr,
            metrics=metrics,
        )

        # 5. Evaluation & Refinement
        tool_step = len(execution_steps)
        final_response, score, is_success, votes = await self._evaluate_response(final_response, user_text, tool_step, _depth=_depth)

        # 6. Update History & Stats
        self._update_history(user_msg, final_response, is_success, score, votes)

        # Auto-maintenance
        self.task_counter += 1
        if self.task_counter >= 10:
            await self._reflect()
            # Evict old engrams (decay-based)
            try:
                evicted = self.memory.decay_old_engrams(max_fallos=3)
                if evicted > 0:
                    logger.info(f"[Memory] Auto-evicted {evicted} stale engrams")
            except Exception as e:
                logger.warning(f"[Memory] Decay failed: {e}")
            self.task_counter = 0

        await self._check_integrity(final_usage.get("prompt_tokens", 0) if final_usage else 0)

        return {
            "response": final_response,
            "steps": execution_steps,
            "sources": extracted_sources,
            "usage": final_usage if final_usage else usage,
            "score": score
        }

    def _update_history(self, user_msg, final_response, is_success, score=None, votes=None):
        self.history.append({"role": "user", "content": user_msg})
        self.history.append({"role": "assistant", "content": final_response})
        if len(self.history) > 20:
            self.history = self.history[-20:]
        self.memory.log_experience(user_msg, final_response, is_success, score, votes)

    async def _evaluate_response(self, response, user_text, tool_step, _depth=0):
        """Evaluates response quality using PRM Scorer and optionally refines."""
        try:
            result = await self.scorer.evaluate(
                response=response, instruction=user_text, turn_num=tool_step,
            )
            score = 0.0
            if result and isinstance(result, dict):
                val = result.get("score")
                if isinstance(val, (int, float)):
                    score = float(val)
            votes = result.get("votes", []) if result and isinstance(result, dict) else []

            max_refinements = 3
            refinement_step = 0

            while score < 0.5 and self.config.get("enable_prm_scorer", True) and refinement_step < max_refinements:
                refinement_step += 1
                print(f"{Colors.YELLOW}[*] Calidad insuficiente ({score:.2f} < 0.5). Refinamiento ({refinement_step}/{max_refinements})...{Colors.END}")

                try:
                    refined_response = await self._process(
                        f"REFINEMENT REQUEST: The previous response was rated {score:.2f}/1.0. "
                        f"Instruction: {user_text}\n"
                        f"Previous Response: {response}\n\n"
                        f"Please provide a corrected, high-quality version. If you lack specific data, "
                        f"USE YOUR TOOLS (SEARCH, WEB_READ) now to find it. "
                        f"Do NOT explain your errors, just deliver the final result.",
                        _depth=_depth + 1,
                    )
                    if isinstance(refined_response, dict):
                        response = refined_response.get("response", response)
                    else:
                        response = str(refined_response)
                except Exception as e:
                    app_logger.warning(f"Refinement process failed: {e}")
                    break

                result = await self.scorer.evaluate(
                    response=response, instruction=user_text, turn_num=tool_step + refinement_step,
                )
                score = 0.0
                if result and isinstance(result, dict):
                    val = result.get("score")
                    if isinstance(val, (int, float)):
                        score = float(val)
                votes = result.get("votes", []) if result and isinstance(result, dict) else []

            is_success = score >= 0.5
            return response, score, is_success, votes

        except Exception as e:
            app_logger.warning(f"PRM evaluation failed: {e}")
            return response, None, False, []

    # --- Evolution & Maintenance ---

    async def _reflect(self):
        print(f"{Colors.YELLOW}[*] Iniciando evolucion autonoma profunda (Dual)...{Colors.END}")
        logs = self.memory.get_recent_logs(50)

        print(f"{Colors.YELLOW}[*] Fase 1: Extrayendo conocimiento factual (Engrams)...{Colors.END}")
        try:
            new_engrams = await self.evolver.extract_engrams(logs)
            for e in new_engrams:
                self.memory.save_engram(e.get("topic", "tema-desconocido"), e.get("content", ""))
                print(f"{Colors.GREEN}[+] Engram memorizado: {e.get('topic')}{Colors.END}")
        except Exception as e:
            app_logger.exception("Error in Engram extraction")
            print(f"{Colors.RED}[!] Error en extraccion de Engrams: {e}{Colors.END}")

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
                name=skill.get("name"), description=skill.get("description"),
                content=skill.get("content"), category=skill.get("category", "forced-evolution")
            )
            print(f"{Colors.GREEN}[+] Evolucion aplicada: {skill.get('name')}{Colors.END}")

        return f"Evolucion Dual completada. Nuevos Engrams memorizados y {len(new_skills)} nuevas directivas anadidas."

    async def _compact_memory(self):
        print(f"{Colors.BLUE}[*] Compactando memoria...{Colors.END}")
        from prompts.templates import COMPACT_PROMPT
        patterns = self.memory.load_patterns()
        if not patterns.strip():
            print(f"{Colors.YELLOW}[i] Memoria vacia, nada que compactar.{Colors.END}")
            return
        prompt = COMPACT_PROMPT.format(patterns=patterns[:4000])
        compacted, _ = await self.brain.chat([{"role": "user", "content": prompt}])
        self.memory.save_pattern(compacted)
        print(f"{Colors.GREEN}[+] Memoria compactada.{Colors.END}")

    async def _check_integrity(self, current_prompt_tokens=0):
        if current_prompt_tokens > 0:
            self.context_mgr.token_count = current_prompt_tokens

        await self.brain.sync_model_context()
        context_info = await self.brain.get_context_info()
        model_context = context_info.get("max", 32000)

        if self.context_mgr.model_context_length != model_context:
            self.context_mgr.update_context_length(model_context)

        self.scorer.prm_model = self.brain.model

        usage_percent = self.context_mgr.usage_percent
        level = self.context_mgr.get_load_level()

        if level == "warning":
            removed = self.context_mgr.deduplicate()
            if removed > 0:
                print(f"{Colors.YELLOW}[*] Anti-Deduplication: {removed} mensajes redundantes eliminados.{Colors.END}")
        elif level in ("critical", "overflow"):
            print(f"{Colors.RED}[!] Anti-Alert ({level}): {usage_percent}%. Limpieza Sentinel...{Colors.END}")
            self.context_mgr.deduplicate()
            await self.consolidator.run_maintenance()
            await self._compact_memory()
            return

        engrams_count = self.memory.count_engrams()
        skills_count = len(self.memory.skills.skills)
        total = engrams_count + skills_count
        thresholds = [20] + list(range(50, 550, 50))

        current_threshold = 0
        for t in thresholds:
            if total >= t:
                current_threshold = t
            else:
                break

        if current_threshold > self.last_maintenance_count:
            print(f"{Colors.CYAN}[*] Anti-Memory Threshold ({total}). Consolidando...{Colors.END}")
            await self.consolidator.run_maintenance()
            self.last_maintenance_count = current_threshold

    async def _renew_system(self):
        print(f"{Colors.BLUE}[*] Iniciando ciclo de renovacion...{Colors.END}")
        try:
            pattern = re.escape(os.path.join(self.base_dir, 'server.py'))
            subprocess.run(["pkill", "-f", pattern], capture_output=True)
            print(f"{Colors.BLUE}[*] Servidores previos detenidos.{Colors.END}")

            python_exe = "python3"
            venv_python = os.path.join(self.base_dir, "venv/bin/python3")
            if os.path.exists(venv_python):
                python_exe = venv_python

            server_script = os.path.join(self.base_dir, "server.py")
            proc = subprocess.Popen(
                [python_exe, server_script],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL, cwd=self.base_dir
            )
            self.server_proc = proc
            print(f"{Colors.GREEN}[+] Nuevo servidor iniciado con el codigo actualizado.{Colors.END}")

            await asyncio.sleep(1)
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    health_res = await client.get("http://127.0.0.1:8000/health", timeout=2)
                    if health_res.status_code == 200:
                        return "Sistema renovado. El dashboard y el servidor ahora corren con la ultima version."
                    else:
                        return f"Servidor iniciado pero salud no confirmada (Status: {health_res.status_code})."
            except Exception as e:
                return f"Servidor iniciado pero no se pudo contactar el endpoint de salud: {e}"
        except Exception as e:
            return f"Error al renovar: {e}"

    # --- CLI Entry Point ---

    def run(self):
        import signal
        signal.signal(signal.SIGINT, lambda sig, frame: os._exit(0))

        provider_name = type(self.brain).__name__.lower()
        is_local = "lmstudio" in provider_name or "ollama" in provider_name
        display_banner(self.console, is_local)

        try:
            asyncio.run(self._async_run(is_local))
        except KeyboardInterrupt:
            pass
        finally:
            os._exit(0)

    async def _async_run(self, is_local: bool):
        # Share the event loop with MemoryManager to prevent async leak
        self.memory._event_loop = asyncio.get_running_loop()

        try:
            if not await self.brain.check_connection():
                self.console.print(f"[bold yellow][!] Advertencia: No se pudo conectar con el proveedor seleccionado.[/]")
                self.console.print(f"[bold yellow]    Asegurate de que el servidor local o tu API key esten configurados.[/]\n")
        except Exception as e:
            self.console.print(f"[bold red][!] Error critico verificando conexion: {e}[/]")
        await self._async_input_loop(is_local)

    async def _async_input_loop(self, is_local: bool):
        prompt_text = "Anti@Local" if is_local else "Anti@Cloud"
        prompt_color = "green" if is_local else "blue"

        self.console.print("\n[bold magenta]Bienvenido al nucleo de Anti-Agent. Escribe [bold cyan]'help'[ /bold cyan] para ver comandos.[/bold magenta]")

        while self.is_running:
            try:
                user_input = await asyncio.to_thread(self.console.input, f"[{prompt_color} bold]>>> {prompt_text}[/]")
                user_input = user_input.strip()

                if not user_input:
                    continue

                if user_input.lower() in ["exit", "quit"]:
                    self.is_running = False
                    self.console.print(f"\n[bold blue][*] Apagando sistemas... Hasta pronto![/]")
                    break

                with self.console.status(f"[bold yellow]Procesando...[/]", spinner="dots"):
                    result = await self.handle_command(user_input)

                if result:
                    if isinstance(result, dict) and "response" in result:
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

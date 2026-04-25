import os
import json
import re
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

from core.brain import Brain
from core.memory import MemoryManager
from core.context_manager import ContextManager
from core.scorer import PRMScorer
from core.evolver import SkillEvolver
from core.consolidator import MemoryConsolidator
from core.tools import duckduckgo_search, fetch_url_text, autonomous_research, write_file, read_file, run_local_command
from core.document_parser import parse_document
from prompts.system import build_system_prompt
from prompts.templates import REASONER_PROMPT, REFLECT_PROMPT, COMPACT_PROMPT, IMPORTANCE_PROMPT


class Colors:
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BOLD = "\033[1m"
    END = "\033[0m"


def print_header(name="ANTI-AGENT"):
    print(f"{Colors.CYAN}{Colors.BOLD}")
    print("=" * 60)
    print(f"   {name.upper()}: AUTONOMOUS EVOLVING SYSTEM")
    print("=" * 60)
    print(f"{Colors.END}")


class AntiAgent:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        self.config_path = os.path.join(self.base_dir, "config.json")
        self.config = self._load_config()

        # Inicializar proveedor (auto-detectar o específico)
        from core.providers import create_provider, auto_create
        
        provider_type = self.config.get("provider", "auto")
        if provider_type == "auto":
            # Auto-detectar proveedor
            try:
                self.brain = auto_create(
                    model=self.config.get("model"),
                    timeout=self.config.get("timeout", 120)
                )
                print(f"[*] Proveedor auto-detectado: {type(self.brain).__name__}")
            except Exception as e:
                # Fallback a LM Studio
                print(f"[!] Auto-detección falló: {e}. Usando LM Studio por defecto.")
                self.brain = create_provider(
                    "lmstudio",
                    base_url=self.config.get("lm_studio_url", "http://127.0.0.1:1234/v1"),
                    model=self.config.get("model")
                )
        else:
            # Proveedor específico
            url_config = self.config.get(f"{provider_type}_url", 
                          self.config.get("lm_studio_url", "http://127.0.0.1:1234/v1"))
            self.brain = create_provider(
                provider_type,
                base_url=url_config,
                model=self.config.get("model")
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
        url = self.config.get("lm_studio_url", "http://127.0.0.1:1234/v1")
        self.scorer = PRMScorer(prm_url=url, prm_model="local-model")
        self.evolver = SkillEvolver(base_url=url, model="local-model")
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

    # --- CLI Loop ---

    def run(self):
        name = self.config.get("agent_name", "ANTI-AGENT")
        print_header(name)

        if not asyncio.run(self.brain.check_connection()):
            url = self.config.get("lm_studio_url", "http://127.0.0.1:1234/v1")
            print(f"{Colors.YELLOW}[!] No se pudo conectar con LM Studio en {url}.{Colors.END}")
            print(f"{Colors.YELLOW}    Asegurate de que el servidor local este encendido.{Colors.END}\n")

        while self.is_running:
            try:
                user_input = input(f"{Colors.GREEN}{Colors.BOLD}Anti@Local > {Colors.END}").strip()
                if not user_input:
                    continue

                if user_input.lower() in ["exit", "quit"]:
                    self.is_running = False
                    print(f"{Colors.BLUE}Apagando sistema...{Colors.END}")
                    break

                result = asyncio.run(self.handle_command(user_input))
                if result:
                    if isinstance(result, dict) and "response" in result:
                        print(f"\n{result['response']}\n")
                    else:
                        print(f"\n{result}\n")
            except KeyboardInterrupt:
                break

    # --- Command Handler ---

    async def handle_command(self, cmd, image_data=None):
        cmd_lower = cmd.lower().strip()

        if cmd_lower == "help":
            return self._show_help()
        elif cmd_lower == "status":
            return await self._show_status()
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
        elif cmd_lower == "benchmark":
            return await self._run_benchmark()
        else:
            return await self._process(cmd, image_data=image_data)


    # --- Core Processing ---

    async def _process(self, user_msg, image_data=None):
        print(f"{Colors.CYAN}[*] Pensando...{Colors.END}")

        name = self.config.get("agent_name", "Anti")
        personality = self.config.get("personality", "Sos un agente autonomo avanzado.")
        
        # LECTURA MODE: detect @mentions to load a local document as exclusive context
        user_text = user_msg if isinstance(user_msg, str) else str(user_msg)
        
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

        system_prompt = build_system_prompt(
            name=name,
            personality=personality,
            omni_context=omni_context
        )

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

        # Build user content (multimodal support)
        if image_data:
            print(f"{Colors.YELLOW}[i] Imagen recibida para analisis.{Colors.END}")
            user_content = [
                {"type": "text", "text": user_msg if user_msg else "Analiza esta imagen."},
                {"type": "image_url", "image_url": {"url": image_data}}
            ]
        else:
            user_content = user_msg

        # Build conversation thread
        messages = [{"role": "system", "content": system_prompt}]

        for msg in self.history:
            if isinstance(msg["content"], list):
                text = next(
                    (item["text"] for item in msg["content"] if item["type"] == "text"),
                    "Imagen previa"
                )
                messages.append({"role": msg["role"], "content": text})
            else:
                messages.append(msg)

        messages.append({"role": "user", "content": user_content})

        # Main Chat Inference
        try:
            response, usage = await self.brain.chat(messages)
            prompt_tokens = usage.get("prompt_tokens", 0)
            self.context_mgr.token_count = prompt_tokens
        except Exception as e:
            return f"Error en inferencia: {e}"

        # Handle both tuple (fixed) and string (legacy) error responses
        response_str = response if isinstance(response, str) else response[0] if isinstance(response, tuple) else str(response)
        if "Error conectando con LM Studio" in response_str:
            print(f"{Colors.RED}[!] {response_str}{Colors.END}")
            return f"No pude procesar tu solicitud. Error de LM Studio: {response_str}"

        # Clean model artifacts
        response = response.replace("<thought>", "").replace("</thought>", "").strip()

        # --- ReAct Tool Loop (up to 10 iterations for EXTREME mode) ---
        MAX_TOOL_STEPS = 10
        tool_step = 0
        execution_steps = []
        extracted_sources = {}

        while tool_step < MAX_TOOL_STEPS:
            tool_triggered = False
            tool_context = None
            current_step = {"step": tool_step + 1, "tool": None, "query": None, "result_summary": None}

            # Detect which tool the model wants to use
            if "[SEARCH:" in response:
                match = re.search(r"\[SEARCH:\s*(.*?)\]", response)
                if match:
                    query = match.group(1).strip()
                    print(f"{Colors.YELLOW}[*] [{tool_step+1}/5] SEARCH: {query}...{Colors.END}")
                    result = duckduckgo_search(query)
                    tool_triggered = True
                    current_step.update({"tool": "SEARCH", "query": query, "result_summary": result[:200] + "..."})
                    
                    # Extract URLs for UI
                    found_urls = re.findall(r'URL: (https?://[^\s\n\]]+)', result)
                    for url in found_urls:
                        if url not in extracted_sources.values():
                            extracted_sources[len(extracted_sources) + 1] = url
                            
                    tool_context = f"[RESULTADO SEARCH]\n{result}\n\nContinua con la tarea. Podes usar otra herramienta si necesitas mas informacion, o entrega la respuesta final."

            elif "[FETCH:" in response:
                match = re.search(r"\[FETCH:\s*(.*?)\]", response)
                if match:
                    url = match.group(1).strip()
                    print(f"{Colors.YELLOW}[*] [{tool_step+1}/5] FETCH: {url}...{Colors.END}")
                    result = fetch_url_text(url)
                    tool_triggered = True
                    current_step.update({"tool": "FETCH", "query": url, "result_summary": result[:200] + "..."})
                    if url not in extracted_sources.values():
                        extracted_sources[len(extracted_sources) + 1] = url
                    tool_context = f"[CONTENIDO WEB]\n{result}\n\nContinua con la tarea. Podes usar otra herramienta o entregar la respuesta final."

            elif "[RESEARCH:" in response:
                match = re.search(r"\[RESEARCH:\s*(.*?)\]", response)
                if match:
                    query = match.group(1).strip()
                    print(f"{Colors.YELLOW}[*] [{tool_step+1}/5] RESEARCH PROFUNDO: {query}...{Colors.END}")
                    result = autonomous_research(query)
                    tool_triggered = True
                    current_step.update({"tool": "RESEARCH", "query": query, "result_summary": "Informe consolidado generado."})
                    
                    # Extract URLs for UI
                    found_urls = re.findall(r'URL: (https?://[^\s\n\]]+)', result)
                    for url in found_urls:
                        if url not in extracted_sources.values():
                            extracted_sources[len(extracted_sources) + 1] = url
                            
                    tool_context = f"[INFORME DE INVESTIGACION AUTONOMA]\n{result}\n\nAnaliza todo el informe. Podes usar WRITE para guardar el resultado, o entrega la respuesta final."

            elif "[WRITE:" in response:
                match = re.search(r"\[WRITE:\s*(.*?)\s*\|\s*(.*?)\]", response, re.DOTALL)
                if match:
                    filename = match.group(1).strip()
                    content = match.group(2).strip()
                    print(f"{Colors.YELLOW}[*] [{tool_step+1}/5] WRITE: {filename}...{Colors.END}")
                    result = write_file(filename, content)
                    tool_triggered = True
                    current_step.update({"tool": "WRITE", "query": filename, "result_summary": result})
                    tool_context = f"[RESULTADO ESCRITURA]\n{result}\n\nConfirma al usuario que el archivo esta listo."

            elif "[READ:" in response:
                match = re.search(r"\[READ:\s*(.*?)\]", response)
                if match:
                    filename = match.group(1).strip()
                    print(f"{Colors.YELLOW}[*] [{tool_step+1}/5] READ (Workspace): {filename}...{Colors.END}")
                    result = read_file(filename)
                    tool_triggered = True
                    current_step.update({"tool": "READ", "query": filename, "result_summary": result[:200] + "..."})
                    tool_context = f"[CONTENIDO DEL ARCHIVO]\n{result}\n\nAnaliza el contenido y responde."

            elif "[ANALYZE:" in response:
                match = re.search(r"\[ANALYZE:\s*(.*?)\]", response)
                if match:
                    path = match.group(1).strip()
                    print(f"{Colors.YELLOW}[*] [{tool_step+1}/5] ANALYZE: {path}...{Colors.END}")
                    result = parse_document(path)
                    tool_triggered = True
                    current_step.update({"tool": "ANALYZE", "query": path, "result_summary": result[:200] + "..."})
                    tool_context = f"[ANALISIS DE DOCUMENTO]\n{result}\n\nAnaliza el contenido extraido. Si era un PDF o codigo, procesalo adecuadamente."

            elif "[RUN:" in response:
                match = re.search(r"\[RUN:\s*(.*?)\]", response)
                if match:
                    cmd = match.group(1).strip()
                    print(f"{Colors.YELLOW}[*] [{tool_step+1}/5] RUN COMMAND: {cmd}...{Colors.END}")
                    result = run_local_command(cmd)
                    tool_triggered = True
                    current_step.update({"tool": "RUN", "query": cmd, "result_summary": result[:200] + "..."})
                    tool_context = f"[SALIDA DE COMANDO]\n{result}\n\nAnaliza la salida del comando y decide el siguiente paso."

            if not tool_triggered:
                # No tool called → final response
                break

            execution_steps.append(current_step)
            
            # Feed tool result back to the model
            messages.append({"role": "assistant", "content": response})
            messages.append({"role": "user", "content": tool_context})
            print(f"{Colors.CYAN}[*] Procesando resultado de herramienta...{Colors.END}")
            response, usage = await self.brain.chat(messages)
            prompt_tokens = usage.get("prompt_tokens", 0)
            self.context_mgr.token_count = prompt_tokens
            response = response.replace("<thought>", "").replace("</thought>", "").strip()
            tool_step += 1

        # Reasoner mode: self-critique
        if self.reasoner_mode:
            print(f"{Colors.YELLOW}[*] Reasoner: auto-critica...{Colors.END}")
            critic_prompt = REASONER_PROMPT.format(user_msg=user_msg, response=response)
            response, _ = await self.brain.chat([{"role": "user", "content": critic_prompt}])
            print(f"{Colors.GREEN}[+] Respuesta refinada.{Colors.END}")

        # Evaluate response with PRM Scorer
        is_success = True
        score = 0.0
        votes = []
        try:
            print(f"{Colors.BLUE}[*] Scorer evaluando respuesta...{Colors.END}")
            eval_result = await self.scorer.evaluate(response, user_text)
            score = eval_result["score"]
            votes = eval_result["votes"]
            is_success = score > 0
            print(f"{Colors.GREEN}[+] Score: {score} | Votes: {votes}{Colors.END}")

            # ZERO-SHOT REFLECTION: Si el score es malo, forzamos una correccion
            if score <= 0:
                print(f"{Colors.RED}[!] Respuesta deficiente (Score {score}). Forzando autocorreccion...{Colors.END}")
                correction_prompt = (
                    f"Tu respuesta anterior fue evaluada y considerada ineficiente, redundante o no respondio "
                    f"directamente a la pregunta. Re-escribe la respuesta, aplicando SINTESIS EXTREMA, "
                    f"asegurandote de responder exactamente lo que se pidio: '{user_text}'.\n\n"
                    f"Respuesta rechazada:\n{response}"
                )
                response, _ = await self.brain.chat([{"role": "user", "content": correction_prompt}])
                response = response.replace("<thought>", "").replace("</thought>", "").strip()
                print(f"{Colors.GREEN}[+] Respuesta corregida y lista.{Colors.END}")

        except Exception as e:
            print(f"{Colors.RED}[!] Error en Scorer: {e}{Colors.END}")

        # Log and update history
        self.memory.log_experience(f"Chat: {user_msg}", response, is_success, score, votes)
        
        # ACTUALIZACIÓN DE ESTADÍSTICAS DE USO (Decay System)
        if hasattr(self.memory, 'last_retrieved_topics'):
            for topic in self.memory.last_retrieved_topics:
                self.memory.update_usage_stats(topic, is_success)

        self.history.append({"role": "user", "content": user_msg})
        self.history.append({"role": "assistant", "content": response})
        if len(self.history) > 50:
            self.history = self.history[-50:]

        # Auto-maintenance
        self.task_counter += 1
        if self.task_counter >= 10:
            print(f"{Colors.YELLOW}[*] Auto-reflexión conductual (10 mensajes)...{Colors.END}")
            await self._reflect()
            self.task_counter = 0

        # Autonomous Maintenance by Integrity Matrix (v0.5)
        await self._check_integrity(prompt_tokens)

        # Final structured response for Web UI
        return {
            "response": response,
            "steps": execution_steps,
            "sources": extracted_sources,
            "usage": usage,
            "score": score
        }

    async def _run_benchmark(self):
        from core.benchmark import SentinelGauntlet
        print(f"{Colors.YELLOW}[*] Iniciando protocolo SENTINEL GAUNTLET...{Colors.END}")
        runner = SentinelGauntlet(self)
        report_path = await runner.run()
        msg = f"Benchmark finalizado con exito.\nReporte generado: {report_path}"
        print(f"{Colors.GREEN}[+] {msg}{Colors.END}")
        return msg

    # --- Reasoner ---

    def _toggle_reasoner(self):
        self.reasoner_mode = not self.reasoner_mode
        status = "ACTIVADO" if self.reasoner_mode else "DESACTIVADO"
        msg = f"Modo Reasoner: {status}"
        print(f"{Colors.YELLOW}[*] {msg}{Colors.END}")
        return msg

    async def _force_search(self, query):
        print(f"{Colors.YELLOW}[*] Forzando búsqueda web: {query}...{Colors.END}")
        search_results = duckduckgo_search(query)
        
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
                if os.path.exists(path):
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
            import shutil
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
            print(f"{Colors.RED}[!] Error en extraccion de Engrams: {e}{Colors.END}")

        # 2. Pase Conductual: Refinar Skills
        print(f"{Colors.YELLOW}[*] Fase 2: Analizando {len(logs)} experiencias para destilar mejores practicas...{Colors.END}")
        try:
            new_skills = await self.evolver.evolve(logs, self.memory.skills.skills)
        except Exception as e:
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

    def _show_help(self):
        help_text = """
ANTI-AGENT — COMANDOS

  [Chat]
    Escribi cualquier pregunta y el agente responde.
    search <query>  Fuerza una busqueda web inmediata.

  reasoner    Activa/desactiva auto-critica de respuestas.
  reflect     Analiza experiencias pasadas y genera reglas (evolución).
  memories    Muestra un resumen de la memoria del agente (logs, patrones, engrams).
  engra       Lista todos los engrams (conocimiento persistente) con resumen.
  benchmark   Ejecuta el protocolo SENTINEL GAUNTLET v1.0.
  compact     Comprime la memoria de patrones.
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
            self.context_mgr = ContextManager(model_context)
        
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

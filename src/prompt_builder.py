"""
PromptBuilder — System prompt construction for Anti-Agent.

Handles context assembly: memory, skills, documents, boot payload.
"""

import os
import json
import re
from src.logger import Colors
from prompts.system import build_system_prompt


def build_agent_prompt(
    user_text: str,
    config: dict,
    memory,
    plugin_manager,
    base_dir: str,
) -> str:
    """
    Builds the complete system prompt including omni-context,
    document overrides, skills, and boot payload.
    """
    name = config.get("agent_name", "Anti")
    personality = config.get("personality", "Sos un agente autonomo avanzado.")

    # --- LECTURA MODE: @mentions load local documents ---
    reading_context = None
    locked_to_doc = False
    at_mentions = re.findall(r'@(\S+)', user_text)
    if at_mentions:
        lectura_dir = os.path.join(base_dir, "lectura")
        workspace_dir = os.path.join(base_dir, "workspace")
        loaded_docs = []
        for mention in at_mentions:
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

    # --- OMNISCIENT HIPPOCAMPUS: Retrieve all latent memory ---
    omni_context = memory.retrieve_omni_context(user_text)

    # --- ANTI-MEMORY-CORE: boot_payload.json ---
    boot_payload = {}
    boot_path = os.path.join(base_dir, "memory", "boot_payload.json")
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

    if dynamic_system_directives:
        omni_context = dynamic_system_directives + "\n\n[OMNI_CONTEXT_ARCHIVE]\n" + omni_context

    system_prompt = build_system_prompt(
        name=name,
        personality=personality,
        omni_context=omni_context,
        dynamic_tools=plugin_manager.get_tool_descriptions()
    )

    # --- DYNAMIC SKILL TRIGGER SYSTEM ---
    skills = boot_payload.get("skills")
    if skills:
        active_overrides = []
        for skill in skills:
            kw = skill.get("trigger_keyword")
            if kw:
                if re.search(rf"\b{re.escape(kw)}\b", user_text, re.IGNORECASE):
                    active_overrides.append(
                        f"[SYSTEM OVERRIDE: SKILL ACTIVE]\n"
                        f"Skill: {skill.get('nombre_skill', kw)}\n"
                        f"{skill.get('instrucciones_markdown', '')}\n"
                        f"[/SYSTEM OVERRIDE]"
                    )
        if active_overrides:
            system_prompt += "\n\n" + "\n\n".join(active_overrides)

    # --- LOCKED DOCUMENT MODE ---
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

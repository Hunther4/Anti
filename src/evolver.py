"""
Skill Evolver for Anti-Agent.
Refactored to use requests instead of openai library.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import requests
from datetime import datetime
from typing import Any, Dict, Optional, List

logger = logging.getLogger(__name__)

_SLUG_RE = re.compile(r"^[a-z][a-z0-9-]{1,}$")
_DYN_RE = re.compile(r"^dyn-(\d+)$")

class SkillEvolver:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:1234/v1",
        model: str = "local-model",
        max_new_skills: int = 1,
        max_completion_tokens: int = 3000,
    ):
        self.max_new_skills = max_new_skills
        self.max_completion_tokens = max_completion_tokens
        self._model = model
        self.prm_url = f"{base_url.rstrip('/')}/chat/completions"

    async def evolve(
        self,
        failed_logs: list,
        current_skills: list,
    ) -> list[dict]:
        """
        Analyse failed_logs and propose new skills.
        """
        if not failed_logs:
            return []

        prompt = self._build_analysis_prompt(failed_logs, current_skills)

        try:
            response = await asyncio.to_thread(self._call_llm, prompt)
            raw_skills = self._parse_skills_response(response)
            skills = self._finalise_names(raw_skills)
            return skills[: self.max_new_skills]

        except Exception as e:
            logger.error(f"[SkillEvolver] LLM call failed: {e}", exc_info=True)
            return []

    def _call_llm(self, prompt: str) -> str:
        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.max_completion_tokens,
            "temperature": 0.7
        }
        response = requests.post(self.prm_url, json=payload, timeout=120)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']

    def _build_analysis_prompt(
        self,
        failed_logs: list,
        current_skills: list,
    ) -> str:
        failure_blocks = []
        for i, log in enumerate(failed_logs[:5]):
            task = log.get("task", "")
            result = log.get("result", "")
            score = log.get("score", 0.0)
            failure_blocks.append(
                f"### Falla {i + 1}  (Puntaje={score})\n"
                f"**Tarea/Instruccion:**\n{task}\n"
                f"**Respuesta del Agente:**\n{result[:500]}...\n"
            )

        existing = [s.get("name", "") for s in current_skills]

        return (
            "Sos un Arquitecto de Inteligencia para un sistema agéntico avanzado.\n"
            "Tu trabajo: analizar las experiencias del agente (exitosas y fallidas) y generar reglas de ORO para mejorar su rendimiento.\n\n"
            "CRITERIOS DE EVOLUCIÓN:\n"
            "1. SÍNTESIS EXTREMA: ¿Cómo puede el agente decir lo mismo con menos palabras pero más datos?\n"
            "2. PROCESAMIENTO PREVIO: ¿Qué pasos de razonamiento faltaron para 'destilar' la info antes de responder?\n"
            "3. CALIDAD DE FUENTES: ¿Cómo evitar redundancia entre fuentes similares?\n\n"
            "---\n"
            "## Experiencias Recientes\n\n"
            + "\n\n".join(failure_blocks)
            + "\n\n---\n"
            "## Habilidades Existentes (NO duplicar)\n\n"
            + json.dumps(existing, indent=2)
            + "\n\n---\n"
            "## Instrucciones de Salida\n\n"
            f"Genera **1 a {self.max_new_skills}** nuevas reglas o habilidades. Enfocate en la DENSIDAD INFORMATIVA y la EFICIENCIA de búsqueda.\n\n"
            "Formato JSON:\n"
            "- `name`: slug (ej: `sintesis-de-fuentes`).\n"
            "- `description`: cuándo aplicar.\n"
            "- `content`: Guía Markdown (10-15 líneas) con: Objetivo, Pasos para 'destilar' info, y un **Anti-patrón** (ej: copiar y pegar resúmenes sin analizar).\n"
            "- `category`: `investigacion`, `codigo`, o `general`.\n\n"
            "**Salida:** Devuelve SOLO el array JSON."
        )

    def _parse_skills_response(self, response: str) -> list[dict]:
        clean = re.sub(r"```(?:json)?\s*", "", response).strip()
        j_start = clean.find("[")
        j_end = clean.rfind("]") + 1
        if j_start == -1 or j_end <= j_start:
            return []

        try:
            skills = json.loads(clean[j_start:j_end])
        except json.JSONDecodeError:
            return []

        valid = []
        for s in skills:
            missing = [k for k in ("name", "description", "content") if not s.get(k)]
            if not missing:
                valid.append(s)
        return valid

    def _finalise_names(self, skills: list[dict]) -> list[dict]:
        seen = set()
        result = []
        dyn_counter = 1

        for skill in skills:
            updated = dict(skill)
            name = skill.get("name", "").strip().lower()

            if _SLUG_RE.match(name) and name not in seen:
                pass 
            else:
                name = f"dyn-{dyn_counter:03d}"
                dyn_counter += 1

            seen.add(name)
            updated["name"] = name
            updated["category"] = skill.get("category", "general").strip()
            result.append(updated)

        return result

    # --- Dual Evolution: Factual Engrams ---
    
    def _check_duplicate_engram(self, new_content, engrams_dir):
        """Calcula la similitud de Jaccard con engrams existentes para evitar duplicados."""
        new_tokens = set(re.findall(r'\w+', new_content.lower()))
        if not new_tokens: return False, None

        if not os.path.exists(engrams_dir): return False, None

        for filename in os.listdir(engrams_dir):
            if not filename.endswith(".json"): continue
            try:
                with open(os.path.join(engrams_dir, filename), "r") as f:
                    old_data = json.load(f)
                    old_tokens = set(re.findall(r'\w+', old_data.get("content", "").lower()))
                    
                    if not old_tokens: continue
                    intersection = new_tokens & old_tokens
                    union = new_tokens | old_tokens
                    similarity = len(intersection) / len(union)
                    
                    if similarity > 0.5: # Umbral de duplicidad
                        return True, old_data.get("topic")
        return False, None

    async def extract_engrams(self, logs: List[Dict]) -> List[Dict]:
        """
        Analyze logs to extract factual knowledge (Engrams).
        """
        if not logs:
            return []

        prompt = self._build_engram_prompt(logs)

        try:
            response = await asyncio.to_thread(self._call_llm, prompt)
            return self._parse_engrams_response(response)
        except Exception as e:
            logger.error(f"[SkillEvolver] Engram extraction failed: {e}", exc_info=True)
            return []

    def _build_engram_prompt(self, logs: list) -> str:
        blocks = []
        # Filter for successful tasks where information was found
        successful = [l for l in logs if l.get("success", False) and l.get("score", 0) > 0]
        
        for i, log in enumerate(successful[-5:]):
            blocks.append(f"### Tarea:\n{log.get('task', '')}\n### Resultado:\n{log.get('result', '')[:1000]}\n")

        return (
            "Sos el Hipocampo de un sistema de IA. Tu tarea es extraer CONOCIMIENTO FACTUAL (Engrams) de las recientes investigaciones.\n\n"
            "Un Engram es un dato duro, permanente y valioso que la IA debería recordar para no tener que buscarlo de nuevo en el futuro "
            "(ej: 'DeepSeek R1 fue lanzado en Enero 2025 y tiene 67B de parametros', 'El comando para reiniciar el servidor web es docker-compose restart').\n\n"
            "---\n## Investigaciones Recientes:\n\n"
            + "\n\n".join(blocks)
            + "\n\n---\n"
            "## Instrucciones\n"
            "Extrae hasta 3 Engrams clave basados SOLO en la información anterior.\n"
            "Devuelve SOLO un array JSON válido, donde cada objeto tenga:\n"
            "- `topic`: slug corto del tema (ej: 'deepseek-r1-specs').\n"
            "- `content`: Resumen denso y directo de los hechos.\n\n"
            "Si no hay datos duros valiosos, devuelve un array vacío []."
        )

    def _parse_engrams_response(self, response: str) -> list[dict]:
        clean = re.sub(r"```(?:json)?\s*", "", response).strip()
        j_start = clean.find("[")
        j_end = clean.rfind("]") + 1
        if j_start == -1 or j_end <= j_start:
            return []
        try:
            engrams = json.loads(clean[j_start:j_end])
            return [e for e in engrams if e.get("topic") and e.get("content")]
        except json.JSONDecodeError:
            return []

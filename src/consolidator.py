import os
import json
import asyncio
import re
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

class MemoryConsolidator:
    def __init__(self, memory_manager, evolver):
        self.memory = memory_manager
        self.evolver = evolver

    async def run_maintenance(self):
        """Ejecuta un ciclo completo de mantenimiento autónomo"""
        print("[*] Iniciando consolidación autónoma de memoria...")
        
        # 1. Ejecutar Decay (Limpieza por rendimiento)
        deleted_decay = self.memory.decay_old_engrams()
        if deleted_decay > 0:
            print(f"[+] Decay: {deleted_decay} engrams eliminados.")

        # 2. Consolidación de Engrams (Síntesis)
        consolidated_engrams = await self._consolidate_engrams()
        
        # 3. Consolidación de Skills (Síntesis)
        consolidated_skills = await self._consolidate_skills()

        return {
            "deleted_decay": deleted_decay,
            "consolidated_engrams": consolidated_engrams,
            "consolidated_skills": consolidated_skills
        }

    async def _consolidate_engrams(self):
        """Busca engrams similares y pide al LLM que los combine"""
        engrams_path = self.memory.engrams_path
        files = [f for f in os.listdir(engrams_path) if f.endswith('.json')]
        if len(files) < 2: return 0
        
        # Agrupar por similitud (Jaccard simplificado)
        clusters = []
        processed = set()
        
        for i, f1 in enumerate(files):
            if f1 in processed: continue
            current_cluster = [f1]
            processed.add(f1)
            
            with open(os.path.join(engrams_path, f1), 'r') as f:
                content1 = json.load(f).get('content', '')
                tokens1 = set(content1.lower().split())
            
            for f2 in files[i+1:]:
                if f2 in processed: continue
                with open(os.path.join(engrams_path, f2), 'r') as f:
                    content2 = json.load(f).get('content', '')
                    tokens2 = set(content2.lower().split())
                
                sim = len(tokens1 & tokens2) / len(tokens1 | tokens2) if (tokens1 | tokens2) else 0
                if sim > 0.4: # Threshold de cluster
                    current_cluster.append(f2)
                    processed.add(f2)
            
            if len(current_cluster) > 1:
                clusters.append(current_cluster)

        count = 0
        for cluster in clusters:
            print(f"[*] Consolidando cluster de engrams: {cluster}")
            # Cargar contenidos
            contents = []
            for f in cluster:
                with open(os.path.join(engrams_path, f), 'r') as file:
                    contents.append(json.load(file))
            
            # Pedir al LLM que los sintetice
            merged = await self._ask_llm_to_merge_engrams(contents)
            if merged:
                # Borrar originales
                for f in cluster:
                    os.remove(os.path.join(engrams_path, f))
                # Guardar nuevo
                self.memory.save_engram(merged['topic'], merged['content'])
                count += 1
        return count

    async def _ask_llm_to_merge_engrams(self, contents: List[Dict]):
        prompt = (
            "Sos un Gestor de Memoria. Recibiste estos Engrams redundantes:\n"
            + json.dumps(contents, indent=2) + "\n\n"
            "Sintetizalos en UN SOLO Engram denso, técnico y sin repeticiones.\n"
            "Mantené el formato JSON: {\"topic\": \"...\", \"content\": \"...\"}\n"
            "Devolvé SOLO el JSON."
        )
        try:
            response = await asyncio.to_thread(self.evolver._call_llm, prompt)
            clean = re.sub(r"```(?:json)?\s*", "", response).strip()
            return json.loads(clean[clean.find("{"):clean.rfind("}")+1])
        except (json.JSONDecodeError, asyncio.TimeoutError) as e:
            logger.warning(f"[Consolidator] Error in _ask_llm_to_merge_engrams: {e}")
            return None

    async def _consolidate_skills(self):
        """Busca habilidades similares y las combina"""
        skills_dir = self.memory.skills_dir
        # Obtener nombres de carpetas
        dirs = [d for d in os.listdir(skills_dir) if os.path.isdir(os.path.join(skills_dir, d))]
        if len(dirs) < 2: return 0
        
        clusters = []
        processed = set()
        
        for i, d1 in enumerate(dirs):
            if d1 in processed: continue
            current_cluster = [d1]
            processed.add(d1)
            
            skill_file = os.path.join(skills_dir, d1, "SKILL.md")
            if not os.path.exists(skill_file): continue
            
            with open(skill_file, 'r') as f:
                content1 = f.read()
                tokens1 = set(content1.lower().split())
            
            for d2 in dirs[i+1:]:
                if d2 in processed: continue
                skill_file2 = os.path.join(skills_dir, d2, "SKILL.md")
                if not os.path.exists(skill_file2): continue
                
                with open(skill_file2, 'r') as f:
                    content2 = f.read()
                    tokens2 = set(content2.lower().split())
                
                sim = len(tokens1 & tokens2) / len(tokens1 | tokens2) if (tokens1 | tokens2) else 0
                if sim > 0.35: # Threshold un poco más bajo para skills
                    current_cluster.append(d2)
                    processed.add(d2)
            
            if len(current_cluster) > 1:
                clusters.append(current_cluster)

        count = 0
        for cluster in clusters:
            print(f"[*] Consolidando cluster de skills: {cluster}")
            contents = []
            for d in cluster:
                with open(os.path.join(skills_dir, d, "SKILL.md"), 'r') as file:
                    contents.append(file.read())
            
            merged = await self._ask_llm_to_merge_skills(contents)
            if merged:
                # Borrar originales
                import shutil
                for d in cluster:
                    shutil.rmtree(os.path.join(skills_dir, d))
                
                # Crear nueva carpeta y archivo
                new_dir = os.path.join(skills_dir, merged['name'])
                os.makedirs(new_dir, exist_ok=True)
                with open(os.path.join(new_dir, "SKILL.md"), 'w') as f:
                    f.write(merged['content'])
                count += 1
        return count

    async def _ask_llm_to_merge_skills(self, contents: List[str]):
        prompt = (
            "Sos un Arquitecto de Sistemas. Recibiste estas Skills (reglas) redundantes:\n\n"
            + "\n---\n".join(contents) + "\n\n"
            "Sintetizalas en UNA SOLA Skill maestra, densa y sin repeticiones.\n"
            "Mantené el formato de frontmatter YAML y el contenido Markdown.\n"
            "Devolvé SOLO un JSON con: {\"name\": \"slug-nuevo\", \"content\": \"archivo completo con frontmatter\"}\n"
        )
        try:
            response = await asyncio.to_thread(self.evolver._call_llm, prompt)
            clean = re.sub(r"```(?:json)?\s*", "", response).strip()
            return json.loads(clean[clean.find("{"):clean.rfind("}")+1])
        except (json.JSONDecodeError, asyncio.TimeoutError) as e:
            logger.warning(f"[Consolidator] Error in _merge_skills: {e}")
            return None

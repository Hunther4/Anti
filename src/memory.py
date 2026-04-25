import os
import json
import re
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

from src.skills import SkillManager
from src.archive import ArchiveManager
import hashlib

class MemoryManager:
    # Default: keep max 5000 log lines (rotate older)
    MAX_LOG_LINES = 5000
    
    def __init__(self, memory_path, workspace_path=None):
        self.memory_path = memory_path
        self.logs_path = os.path.join(memory_path, "logs.jsonl")
        self.patterns_path = os.path.join(memory_path, "patterns.md")
        self.engrams_path = os.path.join(memory_path, "engrams")
        self.skills_dir = os.path.join(memory_path, "skills")
        self.usage_stats_path = os.path.join(memory_path, "usage_stats.json")
        self.workspace_path = workspace_path
        self.last_retrieved_topics = []
        
        if not os.path.exists(self.engrams_path):
            os.makedirs(self.engrams_path)
            
        if not os.path.exists(self.skills_dir):
            os.makedirs(self.skills_dir)
            
        self.skills = SkillManager(self.skills_dir)
        
        # Cold Path Initialization
        self.archive = ArchiveManager(os.path.join(memory_path, "cold_archive.db"))

    # --- Workspace helpers ---

    def list_workspace_files(self):
        if self.workspace_path and os.path.exists(self.workspace_path):
            return os.listdir(self.workspace_path)
        return []

    def count_workspace_files(self):
        return len(self.list_workspace_files())

    def count_engrams(self):
        if os.path.exists(self.engrams_path):
            return len(os.listdir(self.engrams_path))
        return 0

    # --- Logging ---

    def log_experience(self, task, result, success, score=None, votes=None):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "task": task,
            "result": result[:2000],
            "success": success,
            "score": score,
            "votes": votes
        }
        
        # Rotate logs if exceeding limit
        if os.path.exists(self.logs_path):
            with open(self.logs_path, "r") as f:
                line_count = sum(1 for _ in f)
            if line_count >= self.MAX_LOG_LINES:
                # Keep last half when rotating
                with open(self.logs_path, "r") as f:
                    lines = f.readlines()
                with open(self.logs_path, "w") as f:
                    f.writelines(lines[line_count // 2:])
                logger.info(f"[Memory] Rotated logs, kept {line_count // 2} entries")
        
        with open(self.logs_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
            
        # Also log to Cold Path for permanent history
        self.archive.log_to_history(entry)

    def get_recent_logs(self, limit=10):
        if not os.path.exists(self.logs_path):
            return []
        with open(self.logs_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            return [json.loads(line) for line in lines[-limit:]]

    # --- Patterns ---

    def save_pattern(self, content):
        with open(self.patterns_path, "w", encoding="utf-8") as f:
            f.write(f"Patrones y Lecciones Aprendidas\nActualizado: {datetime.now()}\n\n{content}")

    def load_patterns(self):
        if os.path.exists(self.patterns_path):
            with open(self.patterns_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def forget(self):
        if os.path.exists(self.patterns_path):
            os.remove(self.patterns_path)
        if os.path.exists(self.logs_path):
            os.remove(self.logs_path)

    # --- Engrams ---

    def save_engram(self, topic, content):
        clean_topic = topic.lower().replace(".json", "").replace(".md", "").replace(" ", "_").replace("/", "_")
        filename = f"{clean_topic}.json"
        filepath = os.path.join(self.engrams_path, filename)

        data = {
            "topic": topic,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        
        # Phase 3: Auto-extract entities when observation is saved
        self._auto_extract_entities(clean_topic, content)
        
        return f"Engram '{topic}' guardado."

    def _auto_extract_entities(self, topic, content):
        """
        Auto-extracts entities from saved observation and stores them.
        Creates entity entries in the knowledge graph.
        
        Args:
            topic: Topic/identifier for the observation (used as observation_id)
            content: Content to extract entities from
        """
        import re
        from collections import Counter
        
        # Usar el topic directamente como observation_id para consistencia
        obs_id = topic
        
        # Extraer entidades simple: palabras clave significativas
        #过滤停用词，只保留 palabras significativas
        STOP_WORDS = frozenset({
            "the", "is", "and", "or", "of", "to", "in", "for", "on", "at",
            "by", "an", "as", "it", "be", "do", "if", "no", "not", "are",
            "was", "were", "been", "has", "have", "had", "this", "that",
            "with", "from", "will", "can", "should", "would", "could",
            "el", "la", "los", "las", "de", "en", "un", "una", "por",
            "para", "con", "sin", "sobre", "entre", " cuando", "donde"
        })
        
        words = re.findall(r'[a-zA-Z0-9]{4,}', content.lower())
        filtered = [w for w in words if w not in STOP_WORDS]
        
        # Top 5 palabras más frecuentes como entidades
        word_counts = Counter(filtered)
        top_entities = word_counts.most_common(5)
        
        # Extraer patrones: TODO/NOTA/FIXME/BUG
        patterns = {
            "TODO": r'(?i)(?:TODO|FIXME|TASK):\s*(.+)',
            "BUG": r'(?i)(?:BUG|ERROR|ISSUE):\s*(.+)',
            "DECISION": r'(?i)(?:DECISION|CHOOSE|PICKED):\s*(.+)',
            "PATTERN": r'(?i)(?:PATTERN|CONVENTION):\s*(.+)'
        }
        
        entity_type_map = {
            "TODO": "task",
            "BUG": "bugfix", 
            "DECISION": "decision",
            "PATTERN": "pattern"
        }
        
        try:
            # Guardar entidades en el archivo de archive
            for entity_val, count in top_entities:
                if len(entity_val) >= 4:  # Ignorar entidades muy cortas
                    success = self.archive.add_entity(obs_id, "keyword", entity_val)
            
            # Buscar patrones especiales
            for pat_name, pat_regex in patterns.items():
                matches = re.findall(pat_regex, content)
                for match in matches:
                    if len(match.strip()) >= 4:
                        entity_type = entity_type_map.get(pat_name, "mention")
                        self.archive.add_entity(obs_id, entity_type, match.strip()[:200])
                        
        except Exception as e:
            logger.warning(f"[Memory] Error en auto-extracción: {e}")

    def _simple_bm25_score(self, query_words, content_lower):
        """Versión simplificada de BM25 para ranking de relevancia."""
        score = 0
        words = content_lower.split()
        if not words: return 0
        
        doc_len = len(words)
        avg_len = 500 # Longitud promedio estimada
        k1 = 1.5
        b = 0.75
        
        for word in set(query_words):
            count = words.count(word)
            if count > 0:
                # TF component
                tf = (count * (k1 + 1)) / (count + k1 * (1 - b + b * (doc_len / avg_len)))
                score += tf
        return score

    def update_usage_stats(self, topic, is_success):
        import json
        stats = {}
        if os.path.exists(self.usage_stats_path):
            try:
                with open(self.usage_stats_path, "r") as f:
                    stats = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"[Memory] Error reading usage stats: {e}")
        
        if topic not in stats:
            stats[topic] = {"usos": 0, "fallos": 0, "ultimo_uso": ""}
            
        stats[topic]["usos"] += 1
        if not is_success:
            stats[topic]["fallos"] += 1
        stats[topic]["ultimo_uso"] = datetime.now().isoformat()
        
        with open(self.usage_stats_path, "w") as f:
            json.dump(stats, f, indent=4)

    def decay_old_engrams(self, max_fallos=3):
        """Elimina engrams que no funcionan o son muy viejos."""
        if not os.path.exists(self.usage_stats_path): return 0
        try:
            with open(self.usage_stats_path, "r") as f:
                stats = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"[Memory] Error reading stats for decay: {e}")
            return 0
            
        deleted_count = 0
        for topic, stat in list(stats.items()):
            should_delete = False
            if stat.get("fallos", 0) >= max_fallos:
                should_delete = True
            
            ultimo = stat.get("ultimo_uso")
            if ultimo:
                delta = datetime.now() - datetime.fromisoformat(ultimo)
                if delta.days > 30:
                    should_delete = True
                    
            if should_delete:
                filename = f"{topic.lower().replace(' ', '_')}.json"
                filepath = os.path.join(self.engrams_path, filename)
                if os.path.exists(filepath):
                    os.remove(filepath)
                    deleted_count += 1
                del stats[topic]
                
        with open(self.usage_stats_path, "w") as f:
            json.dump(stats, f, indent=4)
        return deleted_count

    # Phase 2.3: Access Tracking
    ACCESS_BONUS = 0.2

    def _update_engram_access(self, filepath: str, data: dict) -> float:
        """
        Updates last_accessed_at, applies accessBonus, and recalculates full score.
        Returns the new full score.
        """
        import json
        from datetime import datetime
        
        now = datetime.now().isoformat()
        
        # Get current score (default to 1.0)
        current_score = data.get("score", 1.0)
        
        # 3.2: Apply accessBonus (+0.2)
        new_score = current_score + self.ACCESS_BONUS
        
        # 3.3: Recalculate full score (importance + all bonuses)
        importance = data.get("importance_score", 0.5)
        full_score = importance + new_score
        
        # Update in-memory data
        data["last_accessed_at"] = now
        data["score"] = new_score
        
        # Persist to file
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.warning(f"[Memory] Error updating engram access: {e}")
        
        return full_score

    def search_engrams(self, query):
        """
        Busca engrams relevantes con access tracking (Phase 2.3).
        - Actualiza last_accessed_at en cada access
        - Aplica accessBonus (+0.2) por cada acceso
        - Recalcula score completo después de access
        """
        self.last_retrieved_topics = []
        query_words = query.lower().split()
        if not query_words:
            return "Consulta vacia."

        scored = []
        for filename in os.listdir(self.engrams_path):
            if not filename.endswith(".json"):
                continue
            filepath = os.path.join(self.engrams_path, filename)

            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    content = data.get("content", "")
                    content_lower = content.lower()

                    score = self._simple_bm25_score(query_words, content_lower)

                    if score > 0:
                        # 3.1-3.3: Update access tracking and recalculate score
                        full_score = self._update_engram_access(filepath, data)
                        
                        scored.append({
                            "filename": filename,
                            "topic": data.get("topic", filename),
                            "content": content,
                            "score": full_score  # Use recalculated score with bonuses
                        })
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"[Memory] Error reading engram {filename}: {e}")

        if not scored:
            return "No se encontraron engrams relevantes."

        # U-Shape Ordering: [Top 1, Top 3, ..., Top 2]
        final_results = []
        for i, res in enumerate(scored[:5]):
            topic = res['topic']
            self.last_retrieved_topics.append(topic)
            snippet = res['content'][:1000] + ("..." if len(res['content']) > 1000 else "")
            formatted = f"--- Engram: {topic} (Relevancia: {res['score']:.2f}) ---\n{snippet}"
            
            if i % 2 == 0:
                final_results.append(formatted)
            else:
                final_results.insert(0, formatted)

        return "\n\n".join(final_results)

    def cleanup_engrams(self):
        count = 0
        for f in os.listdir(self.engrams_path):
            full_path = os.path.join(self.engrams_path, f)
            try:
                if os.path.isfile(full_path):
                    os.remove(full_path)
                    count += 1
            except OSError as e:
                logger.warning(f"[Memory] Error removing {f}: {e}")
        return count

    def retrieve_omni_context(self, query: str) -> str:
        """
        Scans Skills, Engrams, and Workspace .md files for relevant context.
        Returns a formatted string to inject as Latent Memory.
        """
        omni_parts = []
        
        # 1. Skills (Behavioral)
        relevant_skills = self.skills.retrieve_relevant(query, top_k=3)
        skills_formatted = self.skills.format_for_prompt(relevant_skills)
        if skills_formatted.strip():
            omni_parts.append(f"### SKILLS ACTIVADAS:\n{skills_formatted}")

        # 2. Engrams (Factual)
        engrams_raw = self.search_engrams(query)
        if "No se encontraron engrams" not in engrams_raw and "Consulta vacia" not in engrams_raw:
            omni_parts.append(f"### ENGRAMS (Conocimiento Previo):\n{engrams_raw}")

        # 3. Workspace .md Files (Local Context)
        if self.workspace_path and os.path.exists(self.workspace_path):
            query_words = query.lower().split()
            scored_files = []
            for filename in os.listdir(self.workspace_path):
                if filename.endswith(".md"):
                    filepath = os.path.join(self.workspace_path, filename)
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            content = f.read()
                            content_lower = content.lower()
                            score = sum(content_lower.count(w) for w in query_words)
                            if score > 0:
                                scored_files.append((filename, score, content))
                    except (IOError, UnicodeDecodeError) as e:
                        logger.warning(f"[Memory] Error reading workspace file {filename}: {e}")
            
            if scored_files:
                scored_files.sort(key=lambda x: x[1], reverse=True)
                md_output = []
                for fname, score, content in scored_files[:2]:
                    snippet = content[:800] + "..." if len(content) > 800 else content
                    md_output.append(f"- Archivo Local '{fname}' (Relevancia: {score}):\n{snippet}")
                
                omni_parts.append(f"### ARCHIVOS LOCALES (.md):\n" + "\n".join(md_output))

        # 4. Cold Archive (Long-term Factual)
        archive_results = self.archive.search_archive(query, limit=3)
        if archive_results:
            archive_fmt = "\n".join([f"- {r['topic']} ({r['timestamp']}): {r['content'][:400]}..." for r in archive_results])
            omni_parts.append(f"### ARCHIVO HISTÓRICO (Cold Path):\n{archive_fmt}")

        if not omni_parts:
            return "No hay contexto latente relevante para esta consulta."
            
        return "\n\n".join(omni_parts)

    # --- Knowledge Graph: Entity Extraction ---

    # Patrones regex para entidades
    PATTERNS = {
        "file": r'(?:src/[^\s/]+(?:\.[pf][ly][oa]?)|[^\s/]+\.(?:py|js|ts|md|go|rs|json|yaml|yml|toml)(?:\s|$|/))',
        "url": r'https?://[^\s<>"{}|\\\^`\[\]]+',
        "package": r'(?:npm|pip|go|cargo|poetry|bundler) install ([^\s]+)'
    }

    def _extract_entities(self, content: str) -> dict:
        """
        Extrae entidades de cualquier tipo usando regex.
        Retorna dict con listas por tipo: {"file": [...], "url": [...], "package": [...]}
        """
        entities = {"file": [], "url": [], "package": []}
        
        # Archivos: busca paths que terminen en extensiones comunes
        file_pattern = r'([a-zA-Z0-9_\-./]+\.(?:py|js|ts|tsx|jsx|md|go|rs|json|yaml|yml|toml|sh|html|css|sql))'
        for match in re.finditer(file_pattern, content):
            path = match.group(1).strip()
            # Filtrar paths típicos que no son archivos
            if not path.startswith('/usr/') and not path.startswith('~'):
                entities["file"].append(path)
        
        # URLs
        url_pattern = r'(https?://[^\s<>"{}|\\\^`\[\]]+)'
        for match in re.finditer(url_pattern, content):
            url = match.group(1).strip()
            # Limpiar trailing punctuación
            url = re.sub(r'[.,;:)>\]}]$', '', url)
            if url not in entities["url"]:
                entities["url"].append(url)
        
# Paquetes: npm install, pip install, go get, cargo install
        package_pattern = r'(?:npm|pip|go|cargo|poetry|bundler) (?:install|get)\s+([^\s]+)'
        for match in re.finditer(package_pattern, content):
            pkg = match.group(1).strip()
            # Limpiar trailing puntuación o version - pero preservar slashes para paths
            pkg = re.sub(r'[;,)<>#].*$', '', pkg)
            entities["package"].append(pkg)
        
        # Eliminar duplicados preservando orden
        for etype in entities:
            seen = set()
            unique = []
            for item in entities[etype]:
                if item not in seen:
                    seen.add(item)
                    unique.append(item)
            entities[etype] = unique[:20]  # Limitar a 20 por tipo
        
        logger.debug(f"[Memory] Extraídas entidades: {sum(len(v) for v in entities.values())} total")
        return entities

    def create_entity(self, observation_id: int, entity_type: str, value: str) -> dict:
        """
        Crea una entidad en el Knowledge Graph.
        Args:
            observation_id: ID de la observación/engram origen
            entity_type: "file", "url", "package"
            value: valor de la entidad
        Returns:
            {"success": bool, "entity_id": int or None, "message": str}
        """
        valid_types = {"file", "url", "package"}
        if entity_type not in valid_types:
            return {"success": False, "entity_id": None, "message": f"Tipo inválido. Usar: {valid_types}"}
        
        if not value or len(value.strip()) < 2:
            return {"success": False, "entity_id": None, "message": "Value demasiado corto"}
        
        try:
            entity_id = self.archive.add_entity(observation_id, entity_type, value.strip())
            if entity_id:
                logger.info(f"[Memory] Entidad creada: {entity_type}={value[:50]} (id={entity_id})")
                return {"success": True, "entity_id": entity_id, "message": f"Entidad {entity_type} creada"}
            return {"success": False, "entity_id": None, "message": "Error guardando entidad"}
        except Exception as e:
            logger.error(f"[Memory] Error create_entity: {e}")
            return {"success": False, "entity_id": None, "message": str(e)}

    def create_edge(self, source_id: int, target_id: int, relation_type: str) -> dict:
        """
        Crea una relación (edge) entre dos entidades.
        Args:
            source_id: ID de la entidad origen
            target_id: ID de la entidad destino
            relation_type: tipo de relación (e.g., "imports", "references", "depends_on", "calls")
        Returns:
            {"success": bool, "edge_id": int or None, "message": str}
        """
        valid_relations = {"imports", "references", "depends_on", "calls", "contains", "uses", "implements", "extends"}
        
        if source_id == target_id:
            return {"success": False, "edge_id": None, "message": "source_id y target_id no pueden ser iguales"}
        
        if relation_type not in valid_relations:
            return {"success": False, "edge_id": None, "message": f"Relación inválida. Usar: {valid_relations}"}
        
        try:
            edge_id = self.archive.add_edge(source_id, target_id, relation_type)
            if edge_id:
                logger.info(f"[Memory] Edge creado: {source_id} --[{relation_type}]--> {target_id} (id={edge_id})")
                return {"success": True, "edge_id": edge_id, "message": f"Edge {relation_type} creado"}
            return {"success": False, "edge_id": None, "message": "Error guardando edge"}
        except Exception as e:
            logger.error(f"[Memory] Error create_edge: {e}")
            return {"success": False, "edge_id": None, "message": str(e)}

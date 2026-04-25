import os
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

from src.skills import SkillManager

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
        return f"Engram '{topic}' guardado."

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

    def search_engrams(self, query):
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
                        scored.append({
                            "filename": filename,
                            "topic": data.get("topic", filename),
                            "content": content,
                            "score": score
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

    # --- Omniscient Hippocampus ---

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

        if not omni_parts:
            return "No hay contexto latente relevante para esta consulta."
            
        return "\n\n".join(omni_parts)

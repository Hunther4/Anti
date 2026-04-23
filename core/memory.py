import os
import json
from datetime import datetime

from core.skills import SkillManager

class MemoryManager:
    def __init__(self, memory_path, workspace_path=None):
        self.memory_path = memory_path
        self.logs_path = os.path.join(memory_path, "logs.jsonl")
        self.patterns_path = os.path.join(memory_path, "patterns.md")
        self.engrams_path = os.path.join(memory_path, "engrams")
        self.skills_dir = os.path.join(memory_path, "skills")
        self.workspace_path = workspace_path

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

    def search_engrams(self, query):
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

                    score = sum(content_lower.count(w) for w in query_words)

                    if score > 0:
                        scored.append({
                            "filename": filename,
                            "topic": data.get("topic", filename),
                            "content": content,
                            "score": score
                        })
            except:
                continue

        if not scored:
            return "No se encontraron engrams relevantes."

        scored.sort(key=lambda x: x['score'], reverse=True)

        output = []
        for res in scored[:3]:
            snippet = res['content'][:1000] + ("..." if len(res['content']) > 1000 else "")
            output.append(f"--- Engram: {res['topic']} (Relevancia: {res['score']}) ---\n{snippet}")

        return "\n\n".join(output)

    def cleanup_engrams(self):
        count = 0
        for f in os.listdir(self.engrams_path):
            full_path = os.path.join(self.engrams_path, f)
            try:
                if os.path.isfile(full_path):
                    os.remove(full_path)
                    count += 1
            except:
                continue
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
                    except:
                        continue
            
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

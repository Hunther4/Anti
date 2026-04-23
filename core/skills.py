import os
import glob
import re

class SkillManager:
    """
    Retrieves skills from a directory of Markdown skill files (SKILL.md format).
    Supports keyword-based retrieval.
    """

    _STOP_WORDS = frozenset({
        "the", "is", "and", "or", "of", "to", "in", "for", "on", "at",
        "by", "an", "as", "it", "be", "do", "if", "no", "not", "are",
        "was", "were", "been", "has", "have", "had", "this", "that",
        "with", "from", "will", "can", "should", "would", "could",
        "use", "when", "any", "all", "each", "every", "more", "than",
        "also", "but", "its", "does", "did", "may", "might", "into",
        "what", "how", "who", "where", "which", "why", "your", "you",
        "skill", "follow", "instead", "before", "after",
    })

    def __init__(self, skills_dir):
        self.skills_dir = skills_dir
        self.skills = self._load_skills()

    def _load_skills(self):
        """Scan skills_dir for */SKILL.md files and parse each into a list."""
        result = []
        if not os.path.exists(self.skills_dir):
            return result

        paths = sorted(glob.glob(os.path.join(self.skills_dir, "*", "SKILL.md")))
        for path in paths:
            skill = self._parse_skill_md(path)
            if skill:
                result.append(skill)
        return result

    def reload(self):
        self.skills = self._load_skills()

    def _parse_skill_md(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = f.read()
        except OSError:
            return None

        if not raw.startswith("---"):
            return None

        end_idx = raw.find("\n---", 3)
        if end_idx == -1:
            return None

        fm_text = raw[3:end_idx].strip()
        body = raw[end_idx + 4:].strip()

        fm = {}
        for line in fm_text.splitlines():
            if ":" in line:
                key, _, val = line.partition(":")
                fm[key.strip()] = val.strip()

        name = fm.get("name", "").strip()
        description = fm.get("description", "").strip()
        category = fm.get("category", "general").strip()

        if not name or not description:
            return None

        return {
            "name": name,
            "description": description,
            "category": category,
            "content": body,
        }

    @staticmethod
    def _stem(word):
        for suffix in ("ation", "tion", "sion", "ment", "ness", "ious",
                        "ical", "ally", "ible", "able", "ting", "ing",
                        "ful", "ous", "ive", "ity", "ise", "ize",
                        "ies", "ily", "ely", "ure", "ant", "ent",
                        "ist", "ism", "ory", "ary",
                        "ly", "ed", "er", "es"):
            if word.endswith(suffix) and len(word) - len(suffix) >= 3:
                return word[: -len(suffix)]
        return word

    @staticmethod
    def _tokenize_text(text):
        raw = re.findall(r'[a-zA-Z0-9]+', text.lower())
        tokens = set()
        for tok in raw:
            if len(tok) >= 3 and tok not in SkillManager._STOP_WORDS:
                stemmed = SkillManager._stem(tok)
                if len(stemmed) >= 3:
                    tokens.add(stemmed)
                else:
                    tokens.add(tok)
        return tokens

    def retrieve_relevant(self, task_description, top_k=6, min_relevance=0.07):
        """Retrieve skills filtered by keyword relevance to the task."""
        if not self.skills:
            return []

        task_terms = self._tokenize_text(task_description)
        if not task_terms:
            return self.skills[:top_k]

        scored = []
        for skill in self.skills:
            skill_text = skill.get("name", "") + " " + skill.get("description", "")
            skill_terms = self._tokenize_text(skill_text)
            
            if not skill_terms:
                continue
                
            intersection = task_terms & skill_terms
            relevance = len(intersection) / min(len(task_terms), len(skill_terms))
            
            if relevance >= min_relevance:
                scored.append((relevance, skill))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [s[1] for s in scored[:top_k]]

    def format_for_prompt(self, skills):
        """Format skill dicts into a block for insertion into a system prompt."""
        if not skills:
            return "No hay habilidades activas para esta tarea."
            
        lines = ["## Habilidades Activas"]
        for skill in skills:
            name = skill.get("name", "")
            description = skill.get("description", "")
            content = skill.get("content", "")
            lines.append(f"\n### {name}")
            if description:
                lines.append(f"_{description}_")
            if content:
                lines.append("")
                lines.append(content)
        return "\n".join(lines)

    def add_skill(self, name, description, content, category="general"):
        """Add a new skill and save it to disk."""
        # Sanitize name for folder
        folder_name = re.sub(r'[^a-zA-Z0-9_-]', '-', name.lower())
        skill_dir = os.path.join(self.skills_dir, folder_name)
        os.makedirs(skill_dir, exist_ok=True)
        
        path = os.path.join(skill_dir, "SKILL.md")
        fm = f"name: {name}\ndescription: {description}\ncategory: {category}"
        text = f"---\n{fm}\n---\n\n{content}\n"
        
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
            
        self.reload()
        return True

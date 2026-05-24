"""
HybridCompactor - Sistema híbrido de compactación para Engram v0.6 FINAL

Este archivo contiene todas las mejoras:
- v0.4: HybridCompactor original
- v0.5: Jaccard deduplication, Matriz de Integridad
- v0.5.1: Role-Aware + Context Guard (FIX)
- v0.6: Presión Adaptativa (Sentinel), Semantic Truncate
"""

import re
import os
import json
from typing import Optional, Callable, List, Dict
from datetime import datetime


class HybridCompactor:
    """Sistema híbrido de compactación."""
    
    DEFAULT_GUIDELINES = """
## PRESERVE (alta prioridad)
- Instrucciones del sistema
- Transacciones recientes (últimas 20)
- Categorías configuradas del usuario
- Balance actual
- Preferencias de formato

## DISCARD (puede comprimir)
- Historial antiguo (>30 días)
- Logs de debug
- Estados UI temporales
- Mensajes repetitivos
"""
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        
        # Configuración sliding window
        self.max_messages = self.config.get("max_messages", 50)
        self.summary_threshold = self.config.get("summary_threshold", 30)
        
        # Configuración overlap
        self.overlap_size = self.config.get("overlap_size", 3)
        
        # Guidelines dinámicos
        self.guidelines = self.DEFAULT_GUIDELINES
        
        # Tracking de failures/successes
        self.failures = []
        self.successes = []
        
        # Preservation layer
        self.storage_path = self.config.get("storage_path", "./.engram_compacted")
        
        # Métricas
        self.compaction_count = 0
        self.total_tokens_saved = 0
        self.messages_deduplicated = 0
        
        # v0.6: Presión Adaptativa (Sentinel)
        self.adaptive_thresholds = {
            "safe": 1.0,      # < 50%: inactivo
            "warning": 0.7,   # 50-85%: normal
            "critical": 0.4,   # 85-95%: agresivo
        }
    
    # ==================== TOKEN COUNTING ====================
    
    def count_tokens(self, text: str) -> int:
        """Cuenta tokens de forma precisa usando regex."""
        if not text:
            return 0
        words = re.findall(r"\b[\w']+\b", text)
        punct = re.findall(r"[^\w\s]", text)
        return len(words) + len(punct)
    
    def count_tokens_estimate(self, text: str) -> int:
        """Estimación rápida - divide por 4 chars."""
        return len(text) // 4
    
    def _messages_tokens(self, messages: List[Dict]) -> int:
        """Cuenta tokens total de mensajes."""
        return sum(self.count_tokens(m.get("content", "")) for m in messages)
    
    # ==================== SLIDING WINDOW ====================
    
    def sliding_window(self, messages: List[Dict]) -> List[Dict]:
        """Aplica sliding window simple."""
        if len(messages) <= self.max_messages:
            return messages
        
        excess = messages[:-self.max_messages]
        summary = self._auto_summary(excess)
        
        result = [{"role": "system", "content": f"[RESUMEN: {summary}]"}]
        result.extend(messages[-self.max_messages:])
        
        return result
    
    def _auto_summary(self, messages: List[Dict]) -> str:
        """Genera summary automático sin LLM."""
        if not messages:
            return "Sin historial"
        
        user_msgs = [m for m in messages if m.get("role") == "user"]
        assistant_msgs = [m for m in messages if m.get("role") == "assistant"]
        
        topics = set()
        for msg in messages:
            content = msg.get("content", "")
            words = re.findall(r"\b(\w{5,})\b", content.lower())
            topics.update(words)
        
        summary = f"{len(messages)} mensajes, {len(user_msgs)} del usuario, {len(assistant_msgs)} del asistente"
        
        if topics:
            top_topics = list(topics)[:5]
            summary += f", temas: {', '.join(top_topics)}"
        
        return summary
    
    # ==================== FAILURE-DRIVEN ====================
    
    def record_result(self, task: str, success: bool, info_used: List[str]):
        """Registra resultado de una tarea."""
        entry = {
            "task": task,
            "info_used": info_used,
            "timestamp": datetime.now().isoformat()
        }
        
        if success:
            self.successes.append(entry)
        else:
            self.failures.append(entry)
        
        if len(self.failures) > 100:
            self.failures = self.failures[-100:]
        if len(self.successes) > 100:
            self.successes = self.successes[-100:]
    
    def optimize_guidelines(self, llm: Optional[Callable] = None) -> str:
        """Optimiza guidelines basándose en failures."""
        if not self.failures:
            return self.guidelines
        
        if llm is None:
            missing_info = set()
            for f in self.failures:
                missing_info.update(f.get("info_used", []))
            
            new_guideline = f"\n## FAILURE-DRIVEN PRESERVE\n"
            new_guideline += f"- Info fallida: {', '.join(list(missing_info)[:10])}\n"
            
            self.guidelines += new_guideline
        else:
            prompt = f"""
Analiza estos failures:
{json.dumps(self.failures[-10:], indent=2)}

Y estos successes:
{json.dumps(self.successes[-10:], indent=2)}

Mejora los compression guidelines.
"""
            new_guidelines = llm(prompt)
            if new_guidelines:
                self.guidelines = new_guidelines
        
        return self.guidelines
    
    # ==================== COMPRESSION ====================
    
    def compress(self, messages: List[Dict], budget_tokens: int) -> List[Dict]:
        """Aplica compresión híbrida."""
        if not messages:
            return messages
        
        total = self._messages_tokens(messages)
        
        if total <= budget_tokens:
            return messages
        
        if len(messages) > self.max_messages:
            messages = self.sliding_window(messages)
            self.compaction_count += 1
        
        total = self._messages_tokens(messages)
        
        if total <= budget_tokens:
            return messages
        
        messages = self._filter_by_guidelines(messages)
        
        total = self._messages_tokens(messages)
        
        if total > budget_tokens:
            messages = self._hard_truncate(messages, budget_tokens)
        
        return messages
    
    def _filter_by_guidelines(self, messages: List[Dict]) -> List[Dict]:
        """Filtra mensajes basándose en guidelines."""
        preserve_roles = {"system", "user"}
        
        preserve_keywords = self._extract_keywords("PRESERVE")
        discard_keywords = self._extract_keywords("DISCARD")
        
        preserve = []
        
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            
            if role in preserve_roles:
                preserve.append(msg)
                continue
            
            content_lower = content.lower()
            
            should_preserve = True
            
            for kw in preserve_keywords:
                if kw.lower() in content_lower:
                    should_preserve = True
                    break
            
            for kw in discard_keywords:
                if kw.lower() in content_lower:
                    should_preserve = False
                    break
            
            if should_preserve:
                preserve.append(msg)
        
        return preserve
    
    def _extract_keywords(self, section: str) -> List[str]:
        """Extrae keywords de una sección de guidelines."""
        keywords = []
        
        lines = self.guidelines.split("\n")
        in_section = False
        
        for line in lines:
            line = line.strip()
            
            if line == f"## {section}":
                in_section = True
                continue
            
            if in_section:
                if line.startswith("## "):
                    break
                if line.startswith("-"):
                    kw = line.lstrip("- ").strip()
                    if kw and len(kw) > 2:
                        keywords.append(kw)
        
        return keywords
    
    def _hard_truncate(self, messages: List[Dict], budget_tokens: int) -> List[Dict]:
        """Truncate directo cuando todo lo demás falla."""
        result = []
        remaining = budget_tokens
        
        for msg in messages:
            content = msg.get("content", "")
            tokens = self.count_tokens(content)
            
            if tokens <= remaining:
                result.append(msg)
                remaining -= tokens
            else:
                chars = remaining * 4
                result.append({
                    "role": msg.get("role", "assistant"),
                    "content": content[:chars] + "\n[TRUNCATED]"
                })
                break
        
        return result
    
    # ==================== PRESERVATION LAYER ====================
    
    def preserve_to_disk(self, messages: List[Dict], label: str) -> str:
        """Persiste mensajes a filesystem."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{self.storage_path}/{label}_{timestamp}.json"
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(messages, f, indent=2, default=str)
        
        return filename
    
    # ==================== U-SHAPE ====================
    
    def ushape_order(self, messages: List[Dict]) -> List[Dict]:
        """U-shape ordering para máxima atención."""
        if len(messages) <= 3:
            return messages
        
        system_msgs = [m for m in messages if m.get("role") == "system"]
        user_msgs = [m for m in messages if m.get("role") == "user"]
        other_msgs = [m for m in messages if m.get("role") not in ["system", "user"]]
        
        high_priority = other_msgs[-2:] if len(other_msgs) > 2 else other_msgs
        low_priority = other_msgs[:-2] if len(other_msgs) > 2 else []
        
        result = []
        result.extend(system_msgs)
        
        for msg in low_priority:
            result.append(msg)
        
        for msg in reversed(high_priority):
            result.append(msg)
        
        result.extend(user_msgs)
        
        return result
    
    # ==================== METRICS ====================
    
    def get_stats(self) -> dict:
        """Retorna estadísticas."""
        failure_rate = 0
        if self.failures or self.successes:
            failure_rate = len(self.failures) / (len(self.failures) + len(self.successes))
        
        return {
            "failure_rate": round(failure_rate, 3),
            "total_failures": len(self.failures),
            "total_successes": len(self.successes),
            "compaction_count": self.compaction_count,
            "tokens_saved": self.total_tokens_saved,
            "messages_deduplicated": self.messages_deduplicated,
        }
    
    # ==================== v0.5: JACCARD DEDUPLICATION ====================
    
    def jaccard_similarity(self, text1: str, text2: str) -> float:
        """Calcula similaridad Jaccard entre dos textos."""
        if not text1 or not text2:
            return 0.0
        
        set1 = set(text1.lower().split())
        set2 = set(text2.lower().split())
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    def deduplicate_messages(self, messages: List[Dict], threshold: float = 0.7) -> List[Dict]:
        """
        Deduplicación Role-Aware + Context Guard v0.5.1.
        """
        if len(messages) <= 6:
            return messages
        
        # Context Guard: últimos 4 protegidos
        preserved = messages[-4:]
        to_process = messages[:-4]
        
        if not to_process:
            return messages
        
        unique = [to_process[0]]
        
        for current in to_process[1:]:
            role = current.get("role", "")
            content = current.get("content", "")
            is_duplicate = False
            
            for existing in unique:
                if role == existing.get("role"):
                    sim = self.jaccard_similarity(content, existing.get("content", ""))
                    if sim >= threshold:
                        is_duplicate = True
                        break
            
            if not is_duplicate:
                unique.append(current)
        
        return unique + preserved
    
    # ==================== v0.6: PRESIÓN ADAPTATIVA ====================
    
    def get_adaptive_threshold(self, usage_percent: float) -> float:
        """Retorna umbral Jaccard según nivel de carga."""
        if usage_percent < 50:
            return 1.0
        elif usage_percent < 85:
            return 0.7
        else:
            return 0.4
    
    def deduplicate_adaptive(self, messages: List[Dict], usage_percent: float) -> List[Dict]:
        """Deduplicación adaptativa según carga."""
        threshold = self.get_adaptive_threshold(usage_percent)
        
        if threshold >= 1.0:
            return messages
        
        return self.deduplicate_messages(messages, threshold=threshold)
    
    # ==================== v0.6: SEMANTIC TRUNCATE ====================
    
    def semantic_truncate(self, messages: List[Dict], max_tokens: int) -> List[Dict]:
        """Semantic Truncate con Mid-Truncation inteligente."""
        if not messages:
            return messages
        
        current_tokens = self._messages_tokens(messages)
        if current_tokens <= max_tokens:
            return messages
        
        # New: simple per-message truncation (no complex blocks)
        result = []
        remaining = max_tokens
        
        for msg in messages:
            tokens = self.count_tokens(msg.get("content", ""))
            
            if tokens <= remaining:
                result.append(msg)
                remaining -= tokens
            elif remaining > 20:
                # Mid-Truncation: inicio + [...] + fin
                content = msg.get("content", "")
                chars = remaining * 4
                half = chars // 2
                
                # Always use mid-truncation if there's enough content
                new_content = content[:half] + "[...SEMANTIC TRUNCATED...]" + content[-half:]
                result.append({"role": msg.get("role", "assistant"), "content": new_content})
                remaining = 0
                break
            else:
                # Simple truncate
                content = msg.get("content", "")
                chars = remaining * 4
                result.append({"role": msg.get("role", "assistant"), "content": content[:chars]})
                break
        
        return result
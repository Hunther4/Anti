import sqlite3
import json
import os
import math
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Phase 2.2: Core Scoring Logic
# typeBonus mapping: bonus applied based on observation type
TYPE_BONUS = {
    "bugfix": 0.5,
    "decision": 0.5,
    "discovery": 0.3,
    "pattern": 0.1,
    # Default for unknown types
    None: 0.0,
    "": 0.0,
}

# Phase 2.3: Access Tracking
ACCESS_BONUS = 0.2


class ArchiveManager:
    """
    Gestiona el 'Cold Path' de la memoria de Anti.
    Almacena engrams antiguos y logs extensos en una base de datos SQLite
    para mantener el 'Hot Path' (JSONs) liviano y rápido.
    """
    
    def __init__(self, db_path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Inicializa las tablas si no existen."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Tabla de Engrams Archivados
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS engram_archive (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    importance_score REAL DEFAULT 0,
                    tags TEXT,
                    score REAL DEFAULT 1.0,
                    last_accessed_at TIMESTAMP
                )
            ''')
            # Tabla de Logs Históricos
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS log_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    task TEXT NOT NULL,
                    result TEXT,
                    success INTEGER,
                    score REAL
                )
            ''')
            # Tabla de Entidades (Knowledge Graph)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS entities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    observation_id TEXT,
                    entity_type TEXT NOT NULL,
                    value TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            ''')
            # Tabla de Relaciones (Edges)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS edges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id INTEGER NOT NULL,
                    target_id INTEGER NOT NULL,
                    relation_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (source_id) REFERENCES entities(id),
                    FOREIGN KEY (target_id) REFERENCES entities(id)
                )
            ''')
            # Índices para mejor rendimiento (Phase 1 requirements)
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_entities_observation_id ON entities(observation_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_edges_source_id ON edges(source_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_edges_target_id ON edges(target_id)')
            conn.commit()

    def archive_engram(self, topic, content, importance=0.5, tags=""):
        """Mueve un engram al archivo frío."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO engram_archive (topic, content, timestamp, importance_score, tags) VALUES (?, ?, ?, ?, ?)",
                    (topic, content, datetime.now().isoformat(), importance, tags)
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"[Archive] Error archivando engram: {e}")
            return False

    def search_archive(self, query, limit=5):
        """
        Busca engrams en el archivo frío por coincidencia de texto.
        Phase 2.3: Actualiza last_accessed_at, aplica accessBonus y recalcula score.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Búsqueda simple por LIKE (podemos mejorar a FTS5 luego)
                cursor.execute(
                    "SELECT id, topic, content, timestamp, score FROM engram_archive WHERE topic LIKE ? OR content LIKE ? ORDER BY importance_score DESC LIMIT ?",
                    (f'%{query}%', f'%{query}%', limit)
                )
                results = cursor.fetchall()
                
                processed_results = []
                for r in results:
                    engram_id = r[0]
                    # 3.1: Update last_accessed_at
                    now = datetime.now().isoformat()
                    # 3.2: Get current score and apply accessBonus
                    current_score = r[4] if len(r) > 4 and r[4] is not None else 1.0
                    new_score = current_score + ACCESS_BONUS
                    # 3.3: Recalculate full score (importance + current bonuses + accessBonus)
                    new_importance = r[3] if len(r) > 3 else 0.0
                    full_score = new_importance + new_score
                    
                    cursor.execute(
                        "UPDATE engram_archive SET last_accessed_at = ?, score = ? WHERE id = ?",
                        (now, new_score, engram_id)
                    )
                    
                    processed_results.append({
                        "id": engram_id,
                        "topic": r[1],
                        "content": r[2],
                        "timestamp": r[3],
                        "score": full_score
                    })
                
                conn.commit()
                return processed_results
        except Exception as e:
            logger.error(f"[Archive] Error buscando en archivo: {e}")
            return []

    def log_to_history(self, entry):
        """Guarda un log detallado en el historial de largo plazo."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO log_history (timestamp, task, result, success, score) VALUES (?, ?, ?, ?, ?)",
                    (entry.get('timestamp'), entry.get('task'), entry.get('result'), 
                     1 if entry.get('success') else 0, entry.get('score', 0))
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"[Archive] Error guardando log histórico: {e}")
            return False

    def get_stats(self):
        """Retorna estadísticas del archivo."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM engram_archive")
                engrams = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM log_history")
                logs = cursor.fetchone()[0]
                return {"archived_engrams": engrams, "historical_logs": logs}
        except:
            return {"archived_engrams": 0, "historical_logs": 0}

    # --- Phase 2.4: Auto-Purge System ---

    def _get_low_score_observations(self, threshold=1.0):
        """
        Retorna observaciones con score bajo el threshold especificado.
        
        Args:
            threshold: Score máximo para considerar como "bajo" (default: 1.0)
            
        Returns:
            Lista de diccionarios {
                "id": int,
                "topic": str,
                "content": str,
                "importance_score": float,
                "timestamp": str,
                "last_accessed_at": str or None
            }
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, topic, content, importance_score, timestamp, last_accessed_at 
                    FROM engram_archive 
                    WHERE importance_score < ? 
                    ORDER BY importance_score ASC, timestamp DESC
                    """,
                    (threshold,)
                )
                results = []
                for row in cursor.fetchall():
                    results.append({
                        "id": row[0],
                        "topic": row[1],
                        "content": row[2],
                        "importance_score": row[3],
                        "timestamp": row[4],
                        "last_accessed_at": row[5]
                    })
                return results
        except Exception as e:
            logger.error(f"[Archive] Error en _get_low_score_observations: {e}")
            return []

    def update_observation_score(self, observation_id: int, score_delta: float):
        """
        Actualiza el score de importancia de una observación.
        
        Args:
            observation_id: ID de la observación
            score_delta: Incremento o decremento a aplicar (positivo o negativo)
            
        Returns:
            bool: True si se actualizó correctamente
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Primero verificar que existe
                cursor.execute("SELECT id FROM engram_archive WHERE id = ?", (observation_id,))
                if not cursor.fetchone():
                    logger.warning(f"[Archive] Observación no encontrada: {observation_id}")
                    return False
                    
                # Actualizar score + actualizar last_accessed_at
                cursor.execute(
                    """
                    UPDATE engram_archive 
                    SET importance_score = MAX(0, importance_score + ?),
                        last_accessed_at = ?
                    WHERE id = ?
                    """,
                    (score_delta, datetime.now().isoformat(), observation_id)
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"[Archive] Error actualizando score: {e}")
            return False

    def purge_observations(self, observation_ids: list) -> int:
        """
        Elimina observaciones del archivo (auto-purge).
        
        Args:
            observation_ids: Lista de IDs a eliminar
            
        Returns:
            int: Número de observaciones eliminadas
        """
        if not observation_ids:
            return 0
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                placeholders = ",".join("?" * len(observation_ids))
                cursor.execute(
                    f"DELETE FROM engram_archive WHERE id IN ({placeholders})",
                    observation_ids
                )
                deleted = cursor.rowcount
                conn.commit()
                logger.info(f"[Archive] Auto-purged {deleted} observations")
                return deleted
        except Exception as e:
            logger.error(f"[Archive] Error en purge: {e}")
            return 0

    def add_entity(self, observation_id, entity_type: str, value: str):
        """
        Agrega una entidad al Knowledge Graph.
        Acepta observation_id como string (hash) o int.
        Retorna el ID de la entidad o None si falla.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO entities (observation_id, entity_type, value, timestamp) VALUES (?, ?, ?, ?)",
                    (observation_id, entity_type, value, datetime.now().isoformat())
                )
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"[Archive] Error agregando entidad: {e}")
            return None

    def add_edge(self, source_id: int, target_id: int, relation_type: str) -> int:
        """
        Agrega una relación (edge) entre dos entidades.
        Retorna el ID del edge o None si falla.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Validar que ambas entidades existan
                cursor.execute("SELECT id FROM entities WHERE id IN (?, ?)", (source_id, target_id))
                rows = cursor.fetchall()
                if len(rows) != 2:
                    logger.warning(f"[Archive] Entities no encontradas: {source_id}, {target_id}")
                    return None
                
                cursor.execute(
                    "INSERT INTO edges (source_id, target_id, relation_type, timestamp) VALUES (?, ?, ?, ?)",
                    (source_id, target_id, relation_type, datetime.now().isoformat())
                )
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"[Archive] Error agregando edge: {e}")
            return None

    def get_entities_by_type(self, entity_type: str, limit: int = 50) -> list:
        """取得指定类型的实体列表。"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, observation_id, value, timestamp FROM entities WHERE entity_type = ? ORDER BY id DESC LIMIT ?",
                    (entity_type, limit)
                )
                return [{"id": r[0], "observation_id": r[1], "value": r[2], "timestamp": r[3]} for r in cursor.fetchall()]
        except Exception as e:
            logger.error(f"[Archive] Error obteniendo entidades: {e}")
            return []

    def get_entity_edges(self, entity_id: int) -> list:
        """Obtiene todas las relaciones de una entidad."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT e.id, e.source_id, e.target_id, e.relation_type, e.timestamp FROM edges e WHERE e.source_id = ? OR e.target_id = ?",
                    (entity_id, entity_id)
                )
                return [{"id": r[0], "source_id": r[1], "target_id": r[2], "relation_type": r[3], "timestamp": r[4]} for r in cursor.fetchall()]
        except Exception as e:
            logger.error(f"[Archive] Error obteniendo edges: {e}")
            return []

    # --- Knowledge Graph Phase 3: Relations API ---

    VALID_RELATION_TYPES = frozenset({
        "references", "relates_to", "follows", "supersedes", "contradicts"
    })

    def mem_relate(self, source_id, target_id, relation_type):
        """
        Crea una relación entre dos entidades.
        
        Args:
            source_id: ID de la entidad fuente
            target_id: ID de la entidad objetivo
            relation_type: Uno de: references, relates_to, follows, supersedes, contradicts
            
        Returns:
            Tupla (success: bool, message: str)
        """
        if relation_type not in self.VALID_RELATION_TYPES:
            return (False, f"Tipo de relación inválido: {relation_type}. "
                           f"Válidos: {', '.join(self.VALID_RELATION_TYPES)}")
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Verificar que ambas entidades existen
                cursor.execute("SELECT id FROM entities WHERE id = ?", (source_id,))
                if not cursor.fetchone():
                    return (False, f"Entidad fuente no encontrada: {source_id}")
                cursor.execute("SELECT id FROM entities WHERE id = ?", (target_id,))
                if not cursor.fetchone():
                    return (False, f"Entidad objetivo no encontrada: {target_id}")
                
                # Insertar la relación
                cursor.execute(
                    "INSERT INTO edges (source_id, target_id, relation_type, timestamp) VALUES (?, ?, ?, ?)",
                    (source_id, target_id, relation_type, datetime.now().isoformat())
                )
                conn.commit()
                return (True, f"Relación creada: {source_id} --[{relation_type}]--> {target_id}")
        except Exception as e:
            logger.error(f"[Archive] Error en mem_relate: {e}")
            return (False, f"Error creando relación: {e}")

    def mem_get_relations(self, observation_id, relation_type=None):
        """
        Obtiene relaciones de una observación.
        
        Args:
            observation_id: ID de la observación
            relation_type: Opcional, filtrar por tipo de relación
            
        Returns:
            Lista de diccionarios con {source_id, target_id, relation_type, entity_value}
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Buscar entidades para esta observación
                cursor.execute(
                    "SELECT id, observation_id, entity_type, value FROM entities WHERE observation_id = ?",
                    (observation_id,)
                )
                entities = cursor.fetchall()
                if not entities:
                    return []
                
                entity_ids = [e[0] for e in entities]
                relations = []
                
                for entity_id in entity_ids:
                    # Relaciones salientes
                    query = """
                        SELECT e.source_id, e.target_id, e.relation_type, ent.value
                        FROM edges e
                        JOIN entities ent ON e.target_id = ent.id
                        WHERE e.source_id = ?
                    """
                    params = [entity_id]
                    if relation_type:
                        query += " AND e.relation_type = ?"
                        params.append(relation_type)
                    
                    cursor.execute(query, params)
                    for row in cursor.fetchall():
                        relations.append({
                            "source_id": row[0],
                            "target_id": row[1],
                            "relation_type": row[2],
                            "target_value": row[3]
                        })
                    
                    # Relaciones entrantes
                    query = """
                        SELECT e.source_id, e.target_id, e.relation_type, ent.value
                        FROM edges e
                        JOIN entities ent ON e.source_id = ent.id
                        WHERE e.target_id = ?
                    """
                    params = [entity_id]
                    if relation_type:
                        query += " AND e.relation_type = ?"
                        params.append(relation_type)
                    
                    cursor.execute(query, params)
                    for row in cursor.fetchall():
                        relations.append({
                            "source_id": row[2],  # Original target becomes source in reverse
                            "target_id": row[1],  # Original source becomes target in reverse  
                            "relation_type": row[2],
                            "direction": "incoming",
                            "source_value": row[3]
                        })
                
                return relations
        except Exception as e:
            logger.error(f"[Archive] Error en mem_get_relations: {e}")
            return []

    def mem_graph(self, observation_id, depth=2):
        """
        Recorre el grafo de conocimiento usando BFS desde una observación.
        
        Args:
            observation_id: ID de la observación inicial
            depth: Profundidad máxima de traversal (default: 2)
            
        Returns:
            Diccionario con:
            - nodes: Lista de nodos visitados {id, observation_id, entity_type, value}
            - edges: Lista de relaciones encontradas {source_id, target_id, relation_type}
            - levels: Diccionario indicando nível de cada nodo
        """
        from collections import deque
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 1. Encontrar entidades iniciales para esta observación
                cursor.execute(
                    "SELECT id, observation_id, entity_type, value FROM entities WHERE observation_id = ?",
                    (observation_id,)
                )
                initial_entities = cursor.fetchall()
                if not initial_entities:
                    return {
                        "nodes": [],
                        "edges": [],
                        "levels": {},
                        "root_id": observation_id,
                        "depth": depth,
                        "message": f"No se encontraron entidades para observación: {observation_id}"
                    }
                
                # Inicializar estructuras BFS
                nodes = {}  # id -> {observation_id, entity_type, value}
                edges = []
                levels = {}  # entity_id -> nivel (0 = root)
                visited = set()
                queue = deque()
                
                # Añadir nodos iniciales (nivel 0)
                for ent in initial_entities:
                    entity_id = ent[0]
                    nodes[entity_id] = {
                        "id": entity_id,
                        "observation_id": ent[1],
                        "entity_type": ent[2],
                        "value": ent[3]
                    }
                    levels[entity_id] = 0
                    visited.add(entity_id)
                    queue.append(entity_id)
                
                # BFS traversal
                while queue:
                    current_id = queue.popleft()
                    current_level = levels[current_id]
                    
                    if current_level >= depth:
                        continue
                    
                    next_level = current_level + 1
                    
                    # Buscar neighbors salientes
                    cursor.execute("""
                        SELECT e.target_id, e.relation_type
                        FROM edges e
                        WHERE e.source_id = ?
                    """, (current_id,))
                    
                    for row in cursor.fetchall():
                        target_id = row[0]
                        rel_type = row[1]
                        
                        edges.append({
                            "source_id": current_id,
                            "target_id": target_id,
                            "relation_type": rel_type
                        })
                        
                        if target_id not in visited:
                            # Obtener info del nodo destino
                            cursor.execute(
                                "SELECT id, observation_id, entity_type, value FROM entities WHERE id = ?",
                                (target_id,)
                            )
                            target_ent = cursor.fetchone()
                            if target_ent:
                                nodes[target_id] = {
                                    "id": target_ent[0],
                                    "observation_id": target_ent[1],
                                    "entity_type": target_ent[2],
                                    "value": target_ent[3]
                                }
                                levels[target_id] = next_level
                                visited.add(target_id)
                                queue.append(target_id)
                    
                    # Buscar neighbors entrantes
                    cursor.execute("""
                        SELECT e.source_id, e.relation_type
                        FROM edges e
                        WHERE e.target_id = ?
                    """, (current_id,))
                    
                    for row in cursor.fetchall():
                        source_id = row[0]
                        rel_type = row[1]
                        
                        edges.append({
                            "source_id": source_id,
                            "target_id": current_id,
                            "relation_type": rel_type,
                            "direction": "incoming"
                        })
                        
                        if source_id not in visited:
                            cursor.execute(
                                "SELECT id, observation_id, entity_type, value FROM entities WHERE id = ?",
                                (source_id,)
                            )
                            source_ent = cursor.fetchone()
                            if source_ent:
                                nodes[source_id] = {
                                    "id": source_ent[0],
                                    "observation_id": source_ent[1],
                                    "entity_type": source_ent[2],
                                    "value": source_ent[3]
                                }
                                levels[source_id] = next_level
                                visited.add(source_id)
                                queue.append(source_id)
                
                return {
                    "nodes": list(nodes.values()),
                    "edges": edges,
                    "levels": levels,
                    "root_id": observation_id,
                    "depth": depth,
                    "total_nodes": len(nodes),
                    "total_edges": len(edges)
                }
        except Exception as e:
            logger.error(f"[Archive] Error en mem_graph: {e}")
            return {
                "nodes": [],
                "edges": [],
                "error": str(e)
            }

    # --- Phase 2.2: Core Scoring Logic ---

    def _calculate_score(self, observation_type: str, edges_count: int) -> float:
        """
        Calcula el score base para una observación.
        
        Args:
            observation_type: Tipo de observación (bugfix, decision, discovery, pattern, etc.)
            edges_count: Cantidad de edges/conexiones de la observación
            
        Returns:
            Score en rango [0.0, 5.0]
        """
        # Base score
        score = 1.0
        
        # Type bonus
        type_bonus = TYPE_BONUS.get(observation_type, 0.0)
        score += type_bonus
        
        # Edges contribution: +0.3 per edge
        edges_contribution = edges_count * 0.3
        score += edges_contribution
        
        # Clamp to [0.0, 5.0]
        return max(0.0, min(5.0, score))

    def _apply_age_penalty(self, created_at: datetime) -> float:
        """
        Aplica penalización por edad a una observación.
        
        Penaliza observaciones más antiguas usando logaritmo.
        Formula: agePenalty = -0.05 * log(days_old + 1)
        
        Args:
            created_at: Timestamp de creación de la observación
            
        Returns:
            Valor negativo (penalización) o 0.0 si hay error
        """
        try:
            if created_at is None:
                return 0.0
            
            # Handle both datetime objects and strings
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at)
            
            now = datetime.now()
            delta = now - created_at
            days_old = delta.total_seconds() / 86400.0  # Convert to days
            
            # agePenalty = -0.05 * log(days_old + 1)
            penalty = -0.05 * math.log(days_old + 1)
            
            return penalty
        except Exception as e:
            logger.warning(f"[Archive] Error calculando age penalty: {e}")
            return 0.0

    def _apply_recency_bonus(self, last_accessed: datetime) -> float:
        """
        Aplica bonus por recencia (acceso reciente).
        
        Bonus que aumenta para observaciones accedidas recientemente.
        Formula: recencyBonus = +0.1 * (1 / days_since_access)
        
        Args:
            last_accessed: Timestamp del último acceso
            
        Returns:
            Valor positivo (bonus) o 0.0 si nunca fue accedida o hay error
        """
        try:
            if last_accessed is None:
                return 0.0
            
            # Handle both datetime objects and strings
            if isinstance(last_accessed, str):
                last_accessed = datetime.fromisoformat(last_accessed)
            
            now = datetime.now()
            delta = now - last_accessed
            days_since_access = delta.total_seconds() / 86400.0  # Convert to days
            
            # Avoid division by zero and cap recency bonus
            if days_since_access < 0.001:  # Less than ~15 minutes
                days_since_access = 0.001
            
            # recencyBonus = +0.1 * (1 / days_since_access)
            bonus = 0.1 * (1.0 / days_since_access)
            
            # Cap recency bonus at 1.0 (for very recent access)
            return min(1.0, bonus)
        except Exception as e:
            logger.warning(f"[Archive] Error calculando recency bonus: {e}")
            return 0.0

    def calculate_final_score(
        self,
        observation_type: str,
        edges_count: int,
        created_at: datetime,
        last_accessed: datetime
    ) -> float:
        """
        Calcula el score final combinando todos los componentes.
        
        Formula: score = 1.0 + typeBonus + (edges * 0.3) - agePenalty + recencyBonus
        
        Args:
            observation_type: Tipo de observación
            edges_count: Cantidad de edges
            created_at: Timestamp de creación
            last_accessed: Timestamp del último acceso
            
        Returns:
            Score final en rango [0.0, 5.0]
        """
        base_score = self._calculate_score(observation_type, edges_count)
        age_penalty = abs(self._apply_age_penalty(created_at))  # Make positive for clarity
        recency_bonus = self._apply_recency_bonus(last_accessed)
        
        final_score = base_score - age_penalty + recency_bonus
        
        # Clamp final score to [0.0, 5.0]
        return max(0.0, min(5.0, final_score))

import unittest
import os
import json
import sqlite3
from src.archive import ArchiveManager

class TestAntiV15Updates(unittest.TestCase):
    def setUp(self):
        os.makedirs("workspace", exist_ok=True)
        self.db_path = os.path.join("workspace", "temp_test_db.db")
        # Asegurar que esté limpio antes de empezar
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        self.archive = ArchiveManager(db_path=self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except:
                pass

    def test_knowledge_graph_tables_exist(self):
        # Verificar que las tablas entities y edges se crean correctamente
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [r[0] for r in cursor.fetchall()]
            
            self.assertTrue("entities" in tables)
            self.assertTrue("edges" in tables)

    def test_entity_and_edge_relational_integrity(self):
        # 0. Agregar un engram en el archivo para validar la clave externa/existencia
        self.archive.archive_engram("concept", "Anti-Agent and TF-IDF Ranker setup")
        obs_id = 1 # El ID auto-incremental generado
        
        # 1. Agregar entidades
        self.archive.add_entity(obs_id, "concept", "Anti-Agent")
        self.archive.add_entity(obs_id, "concept", "TF-IDF Ranker")
        
        # Obtener entidades insertadas
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, value FROM entities")
            entities = cursor.fetchall()
            
            self.assertEqual(len(entities), 2)
            source_id, source_val = entities[0]
            target_id, target_val = entities[1]
            
            # 2. Agregar relación (edge)
            cursor.execute(
                "INSERT INTO edges (source_id, target_id, relation_type, timestamp) VALUES (?, ?, ?, ?)",
                (source_id, target_id, "uses", "2026-05-24T19:50:00")
            )
            conn.commit()
            
            # 3. Validar unión relacional (JOIN)
            cursor.execute("""
                SELECT e.relation_type, ent1.value, ent2.value 
                FROM edges e
                JOIN entities ent1 ON e.source_id = ent1.id
                JOIN entities ent2 ON e.target_id = ent2.id
            """)
            edge_data = cursor.fetchone()
            self.assertIsNotNone(edge_data)
            self.assertEqual(edge_data[0], "uses")
            self.assertEqual(edge_data[1], "Anti-Agent")
            self.assertEqual(edge_data[2], "TF-IDF Ranker")

if __name__ == "__main__":
    unittest.main()

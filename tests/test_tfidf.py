import unittest
import os
import shutil
import tempfile
from src.memory import TFIDFContextRanker, MemoryManager

class TestTFIDFAndWorkspace(unittest.TestCase):
    def setUp(self):
        # 1. Preparar un directorio temporal para simular el Workspace recursivo
        self.test_dir = tempfile.mkdtemp()
        
        # Crear subdirectorios anidados
        self.nested_dir1 = os.path.join(self.test_dir, "src", "core")
        self.nested_dir2 = os.path.join(self.test_dir, "docs", "guides")
        self.ignored_dir = os.path.join(self.test_dir, "node_modules", "package")
        
        os.makedirs(self.nested_dir1, exist_ok=True)
        os.makedirs(self.nested_dir2, exist_ok=True)
        os.makedirs(self.ignored_dir, exist_ok=True)

        # 2. Crear archivos de prueba con contenidos conceptualmente diferentes
        # Archivo 1: Python con foco en la TUI de Go
        self.file1_path = os.path.join(self.nested_dir1, "app.py")
        with open(self.file1_path, "w", encoding="utf-8") as f:
            f.write("Esta aplicacion conecta la TUI de Go con Bubbletea y maneja metodos interactivos.")

        # Archivo 2: Documentación sobre Docker sandbox
        self.file2_path = os.path.join(self.nested_dir2, "sandbox.md")
        with open(self.file2_path, "w", encoding="utf-8") as f:
            f.write("Guia para configurar el contenedor Docker con limites estrictos de CPU y memoria cgroups.")

        # Archivo 3: Archivo en carpeta ignorada (no debe leerse)
        self.file3_path = os.path.join(self.ignored_dir, "ignored.js")
        with open(self.file3_path, "w", encoding="utf-8") as f:
            f.write("const secret = 'invisible-hack';")

    def tearDown(self):
        # Eliminar el directorio temporal
        shutil.rmtree(self.test_dir)

    def test_tfidf_ranking_basic(self):
        ranker = TFIDFContextRanker()
        
        docs = [
            {"id": 1, "content": "TUI bubbletea de Go interactiva y reactiva"},
            {"id": 2, "content": "Docker contenedor sandbox con cgroups y limites de CPU"},
            {"id": 3, "content": "Búsqueda vectorial engrams de base de datos SQLite"}
        ]
        
        # Consulta sobre Docker
        ranked_docker = ranker.rank("contenedor Docker limites", docs, top_k=2)
        self.assertEqual(len(ranked_docker), 2)
        # El documento más relevante debe ser el id 2
        self.assertEqual(ranked_docker[0]["id"], 2)
        self.assertTrue(ranked_docker[0]["semantic_score"] > 0.1)

        # Consulta sobre TUI
        ranked_tui = ranker.rank("Go bubbletea interactiva", docs, top_k=2)
        self.assertEqual(ranked_tui[0]["id"], 1)
        self.assertTrue(ranked_tui[0]["semantic_score"] > 0.1)

    def test_recursive_workspace_retrieval(self):
        # Crear MemoryManager apuntando al directorio temporal
        memory_path = tempfile.mkdtemp()
        os.makedirs(os.path.join(memory_path, "engrams"), exist_ok=True)
        os.makedirs(os.path.join(memory_path, "skills"), exist_ok=True)
        
        try:
            mm = MemoryManager(memory_path=memory_path, workspace_path=self.test_dir)
            
            # Consultar sobre Docker
            context = mm.retrieve_omni_context("Docker cpu memoria")
            
            # Debe incluir el archivo 'sandbox.md'
            self.assertIn("sandbox.md", context)
            self.assertIn("CPU y memoria", context)
            
            # NO debe incluir el archivo en node_modules
            self.assertNotIn("ignored.js", context)
            
            # Consultar sobre TUI
            context_tui = mm.retrieve_omni_context("TUI Go Bubbletea")
            self.assertIn("app.py", context_tui)
            self.assertIn("Bubbletea", context_tui)
            
        finally:
            shutil.rmtree(memory_path)

if __name__ == "__main__":
    unittest.main()

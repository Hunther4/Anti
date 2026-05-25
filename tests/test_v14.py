import unittest
import os
import shutil
from src.plugins.core_tools import write_tool
from src.document_parser import parse_document
from src.tools import read_file

class TestAntiV14Updates(unittest.TestCase):
    def setUp(self):
        os.makedirs("workspace", exist_ok=True)

    def tearDown(self):
        # Limpiar archivos creados durante las pruebas
        for filename in ["temp_test_write.txt", "large_temp_file.txt"]:
            filepath = os.path.join("workspace", filename)
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except:
                    pass

    def test_write_tool_multiline_strategy_with_pipes(self):
        # Probar Estrategia 1: separación con \n---\n
        # Contenido real, extenso (>20 caracteres) y con barras verticales '|'
        test_args = "temp_test_write.txt\n---\ndef calculate_sum(a, b):\n    # Esta es una operacion simple | retornamos suma\n    return a + b\n"
        res = write_tool(test_args)
        
        self.assertTrue("creado" in res or "exitosamente" in res)
        
        # Verificar contenido
        content = read_file("temp_test_write.txt")
        self.assertEqual(content, "def calculate_sum(a, b):\n    # Esta es una operacion simple | retornamos suma\n    return a + b")

    def test_write_tool_markdown_codeblock_strategy(self):
        # Probar Estrategia 2: FILE: y bloques de código
        test_args = "FILE: temp_test_write.txt\n```python\ndef greet_user(username):\n    print(f'Hola {username} | Bienvenido al sistema Cosmic')\n```"
        res = write_tool(test_args)
        
        self.assertTrue("creado" in res or "exitosamente" in res)
        content = read_file("temp_test_write.txt")
        self.assertEqual(content, "def greet_user(username):\n    print(f'Hola {username} | Bienvenido al sistema Cosmic')")

    def test_write_tool_legacy_fallback(self):
        # Probar Estrategia 3: barra vertical clásica
        test_args = "temp_test_write.txt | def legacy_function_runner():\n    return 'Running legacy code securely'"
        res = write_tool(test_args)
        
        self.assertTrue("creado" in res or "exitosamente" in res)
        content = read_file("temp_test_write.txt")
        self.assertEqual(content, "def legacy_function_runner():\n    return 'Running legacy code securely'")

    def test_adaptive_chunking_pagination(self):
        # Crear un archivo de prueba con más de 15,000 caracteres
        large_content = "X" * 16000
        filepath = os.path.join("workspace", "large_temp_file.txt")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(large_content)
            
        # 1. Leer sin especificar chunk: debe devolver la primera parte e instrucciones de paginación
        first_read = read_file("large_temp_file.txt")
        self.assertTrue("PAGINACIÓN ANTI" in first_read)
        self.assertTrue("se fragmentó en" in first_read)
        self.assertTrue("large_temp_file.txt#chunk2" in first_read)
        
        # 2. Leer pidiendo el segundo fragmento explícitamente
        second_read = read_file("large_temp_file.txt#chunk2")
        self.assertTrue("Parte 2 de" in second_read)
        # El chunk size es 10,000 con overlap de 1,500
        self.assertTrue(len(second_read) > 5000)

if __name__ == "__main__":
    unittest.main()

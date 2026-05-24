import unittest
import os
import shutil
from src.plugin_manager import PluginManager

class TestSecurityPlugins(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Asegurar que el workspace existe
        self.workspace = "workspace"
        os.makedirs(self.workspace, exist_ok=True)
        
        # Inicializar PluginManager
        self.pm = PluginManager(plugins_dir="src/plugins")

        # 1. Crear un archivo de Python vulnerable de prueba en el workspace
        self.vulnerable_code = """
import os
import subprocess

def insecure_function():
    # 1. Critical Unsafe exec/eval
    eval("print('hack')")
    
    # 2. Critical Unsafe OS Call
    os.system("ls -la")

    # 3. Critical Insecure Subprocess
    subprocess.run("rm -rf /", shell=True)

    # 4. Critical Hardcoded Secret
    super_secret_token = "ghp_12345ABCDEffffffsecretpassword12345"

    try:
        x = 1 / 0
    except ZeroDivisionError:
        # 5. Warning Empty Exception handler
        pass
"""
        self.vuln_filepath = os.path.join(self.workspace, "vuln_test.py")
        with open(self.vuln_filepath, "w", encoding="utf-8") as f:
            f.write(self.vulnerable_code)

        # 2. Crear un archivo .diff vulnerable de prueba
        self.diff_code = """
diff --git a/vuln_test.py b/vuln_test.py
new file mode 100644
--- /dev/null
+++ b/vuln_test.py
+import os
+def hack():
+    secret_password = "supersecret_password_12345"
+    eval("insecure()")
+    subprocess.Popen("malware", shell=True)
"""
        self.diff_filepath = os.path.join(self.workspace, "vuln_test.diff")
        with open(self.diff_filepath, "w", encoding="utf-8") as f:
            f.write(self.diff_code)

    def tearDown(self):
        # Limpiar archivos de prueba
        if os.path.exists(self.vuln_filepath):
            os.remove(self.vuln_filepath)
        if os.path.exists(self.diff_filepath):
            os.remove(self.diff_filepath)

    def test_plugin_loading(self):
        self.assertIn("AST_AUDIT", self.pm.tools)
        self.assertIn("DIFF_AUDIT", self.pm.tools)

    async def test_ast_audit_findings(self):
        result = await self.pm.execute_tool("AST_AUDIT", "vuln_test.py")
        
        # Deben reportarse los 5 issues
        self.assertIn("Unsafe Execution", result)
        self.assertIn("Unsafe OS Execution", result)
        self.assertIn("Insecure Subprocess", result)
        self.assertIn("Hardcoded Secret", result)
        self.assertIn("Empty Exception Handler", result)
        
        # Total reportado
        self.assertIn("Se detectaron **5** vulnerabilidades", result)

    async def test_diff_audit_findings(self):
        result = await self.pm.execute_tool("DIFF_AUDIT", "vuln_test.diff")
        
        self.assertIn("Posible Secreto Hardcodeado", result)
        self.assertIn("Ejecución Insegura", result)
        self.assertIn("Inyección de Comando (Shell=True)", result)
        self.assertIn("se detectaron **3** problemas potenciales", result)

if __name__ == "__main__":
    unittest.main()

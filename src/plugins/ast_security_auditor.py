import ast
import os
import re
from src.plugin_manager import anti_tool

class SecurityASTVisitor(ast.NodeVisitor):
    def __init__(self):
        self.issues = []

    def visit_Call(self, node):
        # 1. Detect eval() and exec()
        if isinstance(node.func, ast.Name):
            if node.func.id in ("eval", "exec"):
                self.issues.append({
                    "line": node.lineno,
                    "severity": "CRITICAL",
                    "type": "Unsafe Execution",
                    "description": f"Uso directo de {node.func.id}(). Posible inyección de código."
                })
        
        # 2. Detect os.system()
        elif isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name) and node.func.value.id == "os":
                if node.func.attr == "system":
                    self.issues.append({
                        "line": node.lineno,
                        "severity": "CRITICAL",
                        "type": "Unsafe OS Execution",
                        "description": "Uso de os.system(). Permite ejecución de comandos arbitrarios sin sanitizar."
                    })
            
            # 3. Detect subprocess with shell=True
            elif isinstance(node.func.value, ast.Name) and node.func.value.id == "subprocess":
                # Check for shell=True keyword argument
                for kw in node.keywords:
                    if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                        self.issues.append({
                            "line": node.lineno,
                            "severity": "CRITICAL",
                            "type": "Insecure Subprocess",
                            "description": f"Llamada a subprocess.{node.func.attr}() con shell=True. Inyección de comando altamente probable."
                        })

        self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        # 4. Detect empty except: pass blocks
        is_empty = False
        if len(node.body) == 1:
            body_node = node.body[0]
            if isinstance(body_node, ast.Pass):
                is_empty = True
            elif isinstance(body_node, ast.Expr) and isinstance(body_node.value, ast.Constant) and body_node.value.value == "...":
                is_empty = True

        if is_empty:
            self.issues.append({
                "line": node.lineno,
                "severity": "WARNING",
                "type": "Empty Exception Handler",
                "description": "Bloque 'except: pass' detectado. Silenciar excepciones oculta bugs catastróficos."
            })
        self.generic_visit(node)

    def visit_Assign(self, node):
        # 5. Detect hardcoded secrets in variable assignments
        # Match variables like api_key, token, password, secret
        secret_keys = re.compile(r'(?i)(api_key|secret|password|token|private_key|auth)')
        for target in node.targets:
            if isinstance(target, ast.Name):
                var_name = target.id
                if secret_keys.search(var_name):
                    # Check if the assigned value is a non-empty string literal
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        val = node.value.value.strip()
                        # Avoid highlighting empty placeholders or environment loads
                        if len(val) > 8 and not val.startswith("os.environ") and not val.startswith("getenv"):
                            # Simple entropy check or just length-based heuristics for demo/safety
                            self.issues.append({
                                "line": node.lineno,
                                "severity": "CRITICAL",
                                "type": "Hardcoded Secret",
                                "description": f"Variable sospechosa '{var_name}' contiene un secreto hardcodeado de longitud {len(val)}."
                            })
        self.generic_visit(node)

@anti_tool(name="AST_AUDIT", description="Analiza sintácticamente un archivo de Python para buscar fallas de seguridad estructurales. Uso: ruta/al/archivo.py")
def ast_audit_tool(raw_args: str) -> str:
    filepath = raw_args.strip()
    
    # Resolve relative path under workspace if not absolute
    if not os.path.isabs(filepath):
        filepath = os.path.join("workspace", filepath)

    if not os.path.exists(filepath):
        return f"[ERROR] El archivo '{filepath}' no existe."

    if not filepath.endswith(".py"):
        return f"[ERROR] AST_AUDIT solo soporta archivos de código Python (.py)."

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            code = f.read()

        tree = ast.parse(code)
        visitor = SecurityASTVisitor()
        visitor.visit(tree)

        if not visitor.issues:
            return f"### 🛡️ Reporte de Auditoría AST para: {os.path.basename(filepath)}\n\n¡Impecable! No se encontraron fallas estructurales de seguridad en el archivo Python."

        lines = [
            f"### 🛡️ Reporte de Auditoría AST para: {os.path.basename(filepath)}",
            f"Se detectaron **{len(visitor.issues)}** vulnerabilidades potenciales.",
            "",
            "| Línea | Severidad | Tipo | Descripción |",
            "| :---: | :---: | :--- | :--- |"
        ]

        for issue in sorted(visitor.issues, key=lambda x: x["line"]):
            severity_str = f"🔴 {issue['severity']}" if issue['severity'] == 'CRITICAL' else f"🟡 {issue['severity']}"
            lines.append(f"| {issue['line']} | {severity_str} | {issue['type']} | {issue['description']} |")

        return "\n".join(lines)

    except SyntaxError as e:
        return f"[ERROR SINTÁCTICO] No se pudo parsear el archivo Python debido a un error de sintaxis:\nLínea {e.lineno}: {e.text.strip() if e.text else ''}\n{e.msg}"
    except Exception as e:
        return f"[ERROR] Error inesperado al analizar el AST: {e}"

import os
import re
import requests
from src.plugin_manager import anti_tool

def fetch_pr_diff(url: str) -> str:
    """Descarga el diff raw de un PR de GitHub."""
    # Asegurar que el URL apunta al archivo .diff
    clean_url = url.strip()
    if "pull" in clean_url and not clean_url.endswith(".diff") and not clean_url.endswith(".patch"):
        # Quitar trailing slashes
        clean_url = clean_url.rstrip("/")
        clean_url += ".diff"
        
    logger_header = {"User-Agent": "Anti-Agent-Auditor-v1.0"}
    try:
        resp = requests.get(clean_url, headers=logger_header, timeout=10)
        if resp.status_code == 200:
            return resp.text
        return f"[ERROR] GitHub retornó estado HTTP {resp.status_code} al solicitar {clean_url}"
    except Exception as e:
        return f"[ERROR] Fallo de red al descargar diff: {e}"

def parse_and_audit_diff(diff_text: str) -> str:
    """Parsea el diff y busca líneas agregadas con código sospechoso."""
    lines = diff_text.splitlines()
    current_file = "Desconocido"
    added_lines = []
    
    # Expresiones regulares para auditoría rápida en diffs
    secret_regex = re.compile(r'(?i)(api_key|secret|password|token)\s*=\s*[\'"][^\'"]{8,}[\'"]')
    unsafe_exec = re.compile(r'\b(eval|exec|os\.system)\s*\(')
    shell_true = re.compile(r'\bsubprocess\..*?\(\s*.*?,?\s*shell\s*=\s*True')
    empty_except = re.compile(r'except\s*:?\s*\n?\s*pass')

    vulnerabilities = []

    for line_num, line in enumerate(lines, 1):
        if line.startswith("+++ b/"):
            current_file = line[6:].strip()
            continue
        
        # Analizar solo líneas agregadas (+) pero ignorando metadatos (+++)
        if line.startswith("+") and not line.startswith("+++"):
            code_line = line[1:].strip()
            
            # 1. Detectar secretos hardcodeados
            if secret_regex.search(code_line):
                vulnerabilities.append({
                    "file": current_file,
                    "line": line_num,
                    "type": "Posible Secreto Hardcodeado",
                    "severity": "CRITICAL",
                    "code": code_line[:60]
                })
            
            # 2. Ejecución insegura
            if unsafe_exec.search(code_line):
                vulnerabilities.append({
                    "file": current_file,
                    "line": line_num,
                    "type": "Ejecución Insegura",
                    "severity": "CRITICAL",
                    "code": code_line[:60]
                })

            # 3. Subprocesos con shell=True
            if shell_true.search(code_line):
                vulnerabilities.append({
                    "file": current_file,
                    "line": line_num,
                    "type": "Inyección de Comando (Shell=True)",
                    "severity": "CRITICAL",
                    "code": code_line[:60]
                })

            # 4. Except pasivo
            if empty_except.search(code_line) or code_line == "except:" or code_line == "except Exception:":
                # Check next line in diff to see if it is + pass
                # simple heuristics for now
                pass

    if not vulnerabilities:
        return "### 🐙 Reporte de Auditoría de Diff / PR\n\n¡Impecable! No se detectaron fallas de seguridad ni secretos hardcodeados en el set de cambios agregados."

    report_lines = [
        "### 🐙 Reporte de Auditoría de Diff / PR",
        f"Se analizaron los cambios del diff y se detectaron **{len(vulnerabilities)}** problemas potenciales en el código agregado.",
        "",
        "| Archivo | Tipo | Severidad | Línea de Diff | Código Sospechoso |",
        "| :--- | :--- | :---: | :---: | :--- |"
    ]

    for v in vulnerabilities:
        severity_str = "🔴 CRITICAL" if v["severity"] == "CRITICAL" else "🟡 WARNING"
        report_lines.append(f"| `{v['file']}` | {v['type']} | {severity_str} | {v['line']} | `{v['code']}` |")

    return "\n".join(report_lines)

@anti_tool(name="DIFF_AUDIT", description="Analiza los cambios de un Pull Request de GitHub o un archivo .diff local para buscar vulnerabilidades. Uso: https://github.com/usuario/repo/pull/1 o ruta/archivo.diff")
def diff_audit_tool(raw_args: str) -> str:
    target = raw_args.strip()
    
    if not target:
        return "[ERROR] Por favor especifica un archivo .diff local o URL de GitHub PR."

    # Detectar si es URL o archivo
    if target.startswith("http://") or target.startswith("https://"):
        if "github.com" not in target:
            return "[ERROR] DIFF_AUDIT actualmente solo soporta URLs de Pull Requests de GitHub."
        
        print(f"[*] Descargando Diff del PR de GitHub: {target}...")
        diff_content = fetch_pr_diff(target)
        if diff_content.startswith("[ERROR]"):
            return diff_content
    else:
        # Resolver ruta local
        filepath = target
        if not os.path.isabs(filepath):
            filepath = os.path.join("workspace", filepath)
        else:
            # Si es absoluto pero no existe, intentar buscarlo relativo a 'workspace/' usando su basename
            if not os.path.exists(filepath):
                filename = os.path.basename(filepath)
                filepath = os.path.join("workspace", filename)

        if not os.path.exists(filepath):
            return f"[ERROR] El archivo de diff local '{filepath}' no existe."

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                diff_content = f.read()
        except Exception as e:
            return f"[ERROR] No se pudo leer el archivo local: {e}"

    return parse_and_audit_diff(diff_content)

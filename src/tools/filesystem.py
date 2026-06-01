import os
import subprocess
import re
from src.logger import AppLogger

app_logger = AppLogger(__name__)

def safe_join(base_dir: str, path: str) -> str:
    """
    Safely joins a base directory with a relative path.
    Prevents directory traversal attacks while allowing nested directories.
    """
    abs_base = os.path.abspath(base_dir)
    abs_path = os.path.abspath(os.path.join(abs_base, path))
    
    if os.path.commonpath([abs_base, abs_path]) != abs_base:
        raise PermissionError(f"[SEGURIDAD] Acceso denegado: intento de escape del workspace ({path}).")
        
    return abs_path

def is_valid_content(content: str) -> bool:
    """
    Validación robusta v2 - balance entre estricto y funcional
    """
    if not content or len(content.strip()) < 20:
        return False
    
    content_lower = content.lower()
    obvious_placeholders = [
        '...', '......', '.........',
        'contenido...', 'contenido extenso',
        'aquí va', 'aqui va', 'placeholder',
        'texto generado', 'resumen en proceso',
        'respuesta:', 'contenido:',
    ]
    
    for p in obvious_placeholders:
        if p in content_lower:
            return False
            
    bad_patterns = [
        r'^\.{3,}$',
        r'^\s*\.{3,}\s*$',
        r'^\[contenido\]$',
        r'^contenido\s+extenso\.?$',
    ]
    
    for pattern in bad_patterns:
        if re.search(pattern, content_lower, re.MULTILINE):
            return False
            
    lines = [l.strip() for l in content.split('\n') if l.strip()]
    sentences = re.split(r'[.!?]+', content)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    if len(lines) < 3 and len(sentences) < 3:
        words = re.findall(r'\b[a-zA-Záéíóúñ]{4,}\b', content)
        if len(words) < 5:
            return False
            
    return True

def write_file(filename: str, content: str, workspace_path: str = "workspace") -> str:
    """
    Write a file to the workspace directory.
    Validates content to prevent placeholders.
    Allows nested directories safely.
    """
    if not is_valid_content(content):
        return "[ERROR] Contenido inválido: se detectaron placeholders o texto insuficiente. Escribí el contenido real y completo."

    try:
        filepath = safe_join(workspace_path, filename)
        
        # Ensure parent directories exist
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        rel_path = os.path.relpath(filepath, workspace_path)
        return f"Archivo '{rel_path}' creado exitosamente en el workspace."
    except PermissionError as pe:
        return str(pe)
    except Exception as e:
        app_logger.exception(f"File write failed for {filename}")
        return f"Error al escribir archivo: {e}"

def read_file(filename: str, workspace_path: str = "workspace") -> str:
    """
    Read a file from the workspace directory using parse_document.
    Supports overlapping chunk pagination and auto-encoding detection.
    """
    try:
        # Extraer el sufijo de chunk si existe
        clean_filename = filename
        chunk_suffix = ""
        if "#chunk" in filename:
            clean_filename, chunk_part = filename.split("#chunk", 1)
            chunk_suffix = "#chunk" + chunk_part

        filepath = safe_join(workspace_path, clean_filename)
        
        # Combinar el path resuelto de forma segura con el fragmento para el parseador
        parse_path = filepath + chunk_suffix
        
        if not os.path.exists(filepath):
            return f"Error: El archivo '{clean_filename}' no existe."
        
        from src.document_parser import parse_document
        return parse_document(parse_path)
    except PermissionError as pe:
        return str(pe)
    except Exception as e:
        app_logger.exception(f"File read failed for {filename}")
        return f"Error al leer archivo: {e}"

def run_local_command(command: str, timeout: int = 45) -> str:
    """
    Executes a shell command in a secure, sandboxed Docker container.
    Mounts the workspace directory to /workspace inside the container.
    """
    import shlex
    
    # 1. Resolve absolute path of the workspace
    workspace_dir = os.path.abspath("workspace")
    if not os.path.exists(workspace_dir):
        os.makedirs(workspace_dir, exist_ok=True)

    # 2. Check if Docker daemon is accessible
    has_docker = False
    try:
        check = subprocess.run(["docker", "ps"], capture_output=True, text=True, timeout=5)
        if check.returncode == 0:
            has_docker = True
    except Exception as e:
        app_logger.debug(f"Docker not available: {e}")

    if has_docker:
        # Run inside Docker sandbox with strict CPU/Memory containment and host user matching
        user_flag = []
        if hasattr(os, "getuid") and hasattr(os, "getgid"):
            user_flag = ["--user", f"{os.getuid()}:{os.getgid()}"]

        docker_cmd = [
            "docker", "run", "--rm",
            "--memory=512m",
            "--cpus=1.0",
            "--network=none",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges:true",
            "--read-only",
            "--tmpfs", "/tmp",
            "--tmpfs", "/root"
        ] + user_flag + [
            "-v", f"{workspace_dir}:/workspace",
            "-w", "/workspace",
            "python:3.12-slim",
            "sh", "-c", command
        ]
        try:
            result = subprocess.run(docker_cmd, capture_output=True, text=True, timeout=timeout)
            output = result.stdout
            if result.stderr:
                cleaned_stderr = "\n".join(
                    [line for line in result.stderr.splitlines() if "Unable to find image" not in line and "Pulling from" not in line]
                ).strip()
                if cleaned_stderr:
                    output += f"\n[ERRORES]\n{cleaned_stderr}"
            
            exit_code = result.returncode
            if exit_code != 0:
                error_type = "GenericExecutionError"
                all_err = (result.stderr or "") + (result.stdout or "")
                if "ModuleNotFoundError" in all_err:
                    error_type = "ModuleNotFoundError"
                elif "SyntaxError" in all_err:
                    error_type = "SyntaxError"
                elif "NameError" in all_err:
                    error_type = "NameError"
                elif "FileNotFoundError" in all_err:
                    error_type = "FileNotFoundError"
                elif "PermissionError" in all_err:
                    error_type = "PermissionError"
                
                telemetry = f"[TELEMETRIA: SANDBOX_FAIL] exit_code={exit_code}, error_type={error_type}\n"
                output = telemetry + output

            return output if output.strip() else "Comando ejecutado en sandbox sin salida."
        except subprocess.TimeoutExpired:
            return "[TELEMETRIA: SANDBOX_FAIL] exit_code=124, error_type=TimeoutExpired\n[TIMEOUT] El comando excedió el límite de 45 segundos en el sandbox."
        except Exception as e:
            app_logger.exception(f"Sandbox execution failed for command: {command[:100]}")
            return f"[TELEMETRIA: SANDBOX_FAIL] exit_code=1, error_type=SandboxStartupError\nError en ejecución del sandbox: {e}"
    else:
        return "[SEGURIDAD] Docker no está disponible y la ejecución local está deshabilitada por políticas de seguridad estrictas."

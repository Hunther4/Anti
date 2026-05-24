import os
import sys
import importlib
import inspect
import logging

logger = logging.getLogger(__name__)

# Global registry for tools
_REGISTRY = {}

def anti_tool(name: str, description: str):
    """
    Decorador para registrar funciones como herramientas de Anti.
    """
    def decorator(func):
        _REGISTRY[name] = {
            "func": func,
            "description": description,
            "name": name
        }
        return func
    return decorator

class PluginManager:
    """
    Gestor dinámico de plugins. Carga automáticamente archivos .py de src/plugins.
    """
    def __init__(self, plugins_dir="src/plugins"):
        self.plugins_dir = plugins_dir
        self.tools = _REGISTRY
        self.load_plugins()

    def load_plugins(self):
        """Escanea la carpeta de plugins y carga los módulos."""
        if not os.path.exists(self.plugins_dir):
            os.makedirs(self.plugins_dir)
            return

        # Derivar el base_module asumiendo que estamos en la raíz del proyecto
        # Si plugins_dir es absoluto, extraer la parte final
        if os.path.isabs(self.plugins_dir):
            rel_path = os.path.relpath(self.plugins_dir, os.getcwd())
            base_module = rel_path.replace(os.sep, ".")
        else:
            base_module = self.plugins_dir.replace(os.sep, ".")

        for filename in os.listdir(self.plugins_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                module_name = f"{base_module}.{filename[:-3]}"
                try:
                    importlib.import_module(module_name)
                    logger.debug(f"[PluginManager] Módulo {module_name} cargado exitosamente.")
                except Exception as e:
                    logger.error(f"[PluginManager] Error cargando plugin {filename}: {e}")

    async def execute_tool(self, name: str, raw_args: str):
        """
        Ejecuta una herramienta registrada pasándole los argumentos crudos.
        Soporta de forma nativa tanto funciones síncronas como asíncronas (corutinas).
        """
        if name not in self.tools:
            return f"[ERROR] Herramienta '{name}' no existe o no está registrada."
        
        try:
            func = self.tools[name]["func"]
            if inspect.iscoroutinefunction(func):
                return await func(raw_args)
            return func(raw_args)
        except Exception as e:
            return f"[ERROR] Fallo al ejecutar '{name}': {str(e)}"

    def get_tool_descriptions(self) -> str:
        """
        Devuelve el bloque de texto con las herramientas para inyectar en el prompt.
        """
        if not self.tools:
            return "- No hay herramientas dinámicas cargadas."
            
        lines = []
        for name, tool in self.tools.items():
            lines.append(f"- [{name}: argumentos]: {tool['description']}")
        return "\n".join(lines)

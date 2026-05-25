# Guía para Desarrolladores de Plugins

Los plugins son el mecanismo de extensión de Anti. Permiten agregar nuevas herramientas que el agente puede invocar durante el loop ReAct.

---

## Cómo funciona

1. Cada plugin es un archivo `.py` en `src/plugins/`.
2. Las funciones se registran con el decorador `@anti_tool(name, description)`.
3. `PluginManager` escanea `src/plugins/` al iniciar, importa los módulos y recoge todas las funciones decoradas.
4. Durante el loop ReAct, el LLM puede invocar `[NOMBRE: argumentos]` y `PluginManager` ejecuta la función.
5. El resultado vuelve al LLM para la siguiente iteración.

---

## API del Decorador

```python
from src.plugin_manager import anti_tool

@anti_tool(name="MI_HERRAMIENTA", description="Descripción clara para el LLM.")
def mi_herramienta(raw_args: str) -> str:
    """
    Procesa raw_args y retorna un string con el resultado.
    """
    pass
```

### Parámetros

| Parámetro | Tipo | Descripción |
| :--- | :--- | :--- |
| `name` | `str` | Nombre único que el LLM usará para invocar la herramienta. En MAYÚSCULAS por convención. |
| `description` | `str` | Descripción que se inyecta en el system prompt. Debe explicar CUÁNDO y CÓMO usar la herramienta. |

### Función

- Recibe **un único string** (`raw_args`) con los argumentos tal como el LLM los escribió.
- Puede ser **síncrona** o **asíncrona** (el `PluginManager` detecta `inspect.iscoroutinefunction` y la ejecuta con `await`).
- Debe retornar un **string** con el resultado (o un mensaje de error).
- El resultado se retroalimenta al LLM textualmente.

---

## Registro en el System Prompt

Cuando el agente construye el system prompt, llama a:

```python
self.plugin_manager.get_tool_descriptions()
```

Que retorna algo como:

```
- [SEARCH: query]: Busca en la web. (Usa Wave Search)
- [WEB_READ: url]: Lee el contenido de cualquier página web...
- [AST_AUDIT: path]: Analiza sintácticamente un archivo Python...
```

El LLM ve estas descripciones y decide cuándo invocar cada herramienta.

---

## Ejemplo: Plugin Template

Creá `src/plugins/mi_plugin.py`:

```python
"""
Mi Plugin - Descripción breve del plugin.

Registra herramientas para hacer X cosa.
"""

import os
import re
import requests
from src.plugin_manager import anti_tool


@anti_tool(
    name="MIPLUGIN_SALUDAR",
    description="Saluda a una persona. Uso: MIPLUGIN_SALUDAR: nombre"
)
def saludar_tool(raw_args: str) -> str:
    """
    Saludar a alguien.
    
    Args:
        raw_args: El nombre de la persona a saludar.
    
    Returns:
        String con el saludo.
    """
    nombre = raw_args.strip()
    if not nombre:
        return "[ERROR] Proporcioná un nombre para saludar."
    
    return f"¡Hola {nombre}! Soy Anti, encantado de conocerte."


@anti_tool(
    name="MIPLUGIN_CONTAR",
    description="Cuenta cuántas líneas tiene un archivo en el workspace. Uso: MIPLUGIN_CONTAR: ruta/archivo.txt"
)
def contar_lineas_tool(raw_args: str) -> str:
    """
    Cuenta líneas de un archivo en el workspace.
    
    Args:
        raw_args: Ruta relativa al archivo dentro de workspace/.
    
    Returns:
        Cantidad de líneas o mensaje de error.
    """
    ruta = raw_args.strip()
    if not ruta:
        return "[ERROR] Proporcioná la ruta del archivo."
    
    ruta_completa = os.path.join("workspace", ruta)
    if not os.path.exists(ruta_completa):
        return f"[ERROR] El archivo '{ruta}' no existe en workspace/."
    
    try:
        with open(ruta_completa, "r", encoding="utf-8") as f:
            lineas = f.readlines()
        return f"El archivo '{ruta}' tiene {len(lineas)} líneas."
    except Exception as e:
        return f"[ERROR] No se pudo leer el archivo: {e}"


@anti_tool(
    name="MIPLUGIN_CLIMA",
    description="Obtiene el clima actual de una ciudad usando wttr.in. Uso: MIPLUGIN_CLIMA: Ciudad"
)
def clima_tool(raw_args: str) -> str:
    """
    Obtiene el clima actual via wttr.in.
    
    Args:
        raw_args: Nombre de la ciudad.
    
    Returns:
        Clima actual en texto plano.
    """
    ciudad = raw_args.strip()
    if not ciudad:
        return "[ERROR] Proporcioná el nombre de una ciudad."
    
    try:
        url = f"https://wttr.in/{ciudad}?format=%C+%t+%h+%w"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return f"Clima en {ciudad}: {resp.text.strip()}"
        return f"[ERROR] No se pudo obtener clima para '{ciudad}'."
    except Exception as e:
        return f"[ERROR] Fallo de conexión: {e}"
```

---

## Directrices para Escribir Plugins

### 1. Parseo de argumentos

El LLM es impredecible con el formato. Hacé el parseo robusto:

```python
def mi_tool(raw_args: str) -> str:
    args = raw_args.strip()
    
    # Intentar múltiples formatos
    if "|" in args:
        partes = args.split("|", 1)
    elif "\n---\n" in args:
        partes = args.split("\n---\n", 1)
    else:
        partes = [args]
    
    # Validar
    if not partes[0]:
        return "[ERROR] Se requiere al menos un argumento."
    ...
```

### 2. Descripciones claras

La `description` es lo único que el LLM ve para decidir. Sé específico:

**Mala**: `"Busca en la web."`

**Buena**: `"Busca información en la web usando SearxNG/DuckDuckGo. Ideal para obtener datos actualizados, noticias, documentación técnica. Uso: SEARCH: consulta de búsqueda"`

### 3. Manejo de errores

Siempre retorná strings de error descriptivos. El LLM los lee y puede corregir su approach:

```python
try:
    resultado = hacer_algo()
    return str(resultado)
except ValueError as e:
    return f"[ERROR] Dato inválido: {e}"
except ConnectionError as e:
    return f"[ERROR] No se pudo conectar: {e}"
```

### 4. Timeouts

Si tu plugin hace llamadas de red, usá timeouts:

```python
requests.get(url, timeout=10)
```

### 5. Seguridad

- Usá `safe_join()` de `src.tools` para prevenir path traversal si trabajás con archivos.
- Validá URLs con `is_safe_url()` para prevenir SSRF.
- Nunca ejecutes comandos del sistema sin pasar por `run_local_command()` (sandbox Docker).

---

## Plugins Existentes como Referencia

| Archivo | Herramientas | Descripción |
| :--- | :--- | :--- |
| `core_tools.py` | SEARCH, RUN, WRITE, READ, FETCH, RESEARCH | Herramientas base del sistema |
| `web_reader.py` | WEB_READ | Scraper web a Markdown limpio |
| `ast_security_auditor.py` | AST_AUDIT | Auditoría de seguridad de código Python |
| `github_diff_auditor.py` | DIFF_AUDIT | Auditoría de PRs y diffs de GitHub |

---

## Debugging

Para ver qué plugins están cargados, usá el comando `plugins` en el agente:

```
Anti@Local > plugins
```

Para ver errores de carga, revisá los logs del agente.

Si un plugin no se carga, verificá:
1. ¿El archivo está en `src/plugins/`?
2. ¿No empieza con `__`?
3. ¿Termina en `.py`?
4. ¿No hay errores de sintaxis o de importación?
5. ¿Las funciones decoradas con `@anti_tool` no tienen parámetros adicionales?

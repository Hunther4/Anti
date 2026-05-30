# Anti‑Agent

![Anti‑Agent Logo](https://raw.githubusercontent.com/your-org/anti-agent/main/assets/logo.png)

---

<!-- EN -->
## Overview
Anti‑Agent is a modular, high‑performance AI assistant framework designed for low‑parameter LLMs (≤ 32 B) and secure, sandboxed execution of commands. It provides a cyber‑punk styled web dashboard and a Bubble Tea TUI, both built with zero‑dependency HTML/CSS and Go respectively. The system integrates multiple LLM providers (OpenAI, Gemini, Ollama, LM‑Studio, etc.) and offers a plugin architecture for extensible tooling.

<!-- ES -->
## Visión General
Anti‑Agent es un marco modular de asistente IA de alto rendimiento pensado para modelos de bajo número de parámetros (≤ 32 B) y ejecución segura de comandos en un sandbox Docker. Ofrece un panel web estilo cyber‑punk y una TUI basada en Bubble Tea, ambos sin dependencias externas. El sistema integra varios proveedores de LLM (OpenAI, Gemini, Ollama, LM‑Studio, etc.) y una arquitectura de plugins para ampliar su funcionalidad.

---

<!-- EN -->
## Key Features
- **Multi‑provider support** – Seamless switching between OpenAI, Gemini, Ollama, LM‑Studio, DeepSeek, Anthropic, Minimax, and custom OpenAI‑compatible APIs.
- **Low‑parameter model focus** – Optimized for models ≤ 32 B (e.g., LLaMA‑7B, Mistral‑7B, Gemma‑2B) with benchmark scripts provided.
- **Secure sandbox** – All `RUN` tool commands are executed inside an isolated Docker container; execution is disabled when Docker is unavailable.
- **Dual UI** – A vibrant web dashboard (`extras/web/`) and a terminal TUI (`launcher.go`) built with Bubble Tea.
- **Plugin system** – Plugins are discovered via `src/plugins/` and can add new tools without modifying core code.
- **Knowledge graph** – Persistent SQLite storage for entities and edges, visualizable via `/api/knowledge_graph`.

<!-- ES -->
## Características Principales
- **Soporte multiproveedor** – Cambio fluido entre OpenAI, Gemini, Ollama, LM‑Studio, DeepSeek, Anthropic, Minimax y APIs compatibles con OpenAI.
- **Enfoque en modelos de bajo parámetro** – Optimizado para modelos ≤ 32 B (p. ej., LLaMA‑7B, Mistral‑7B, Gemma‑2B) con scripts de benchmark incluidos.
- **Sandbox seguro** – Todas las órdenes `RUN` se ejecutan dentro de un contenedor Docker aislado; la ejecución se desactiva cuando Docker no está disponible.
- **Interfaz dual** – Panel web vibrante (`extras/web/`) y TUI de terminal (`launcher.go`) construidos sin dependencias externas.
- **Sistema de plugins** – Los plugins se descubren en `src/plugins/` y pueden agregar nuevas herramientas sin tocar el núcleo.
- **Grafo de conocimiento** – Almacenamiento persistente SQLite para entidades y relaciones, visualizable vía `/api/knowledge_graph`.

---

<!-- EN -->
## Installation
```bash
# Clone the repository
git clone https://github.com/your-org/anti-agent.git
cd anti-agent/Anti

# Install Python dependencies (virtualenv recommended)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Install Go binary (requires Go 1.22+)
./install.sh
```
The installer will:
1. Compile the Go launcher (`launcher.go`) into an executable named `anti`.
2. Create an alias `anti` in `~/.bashrc` that runs the compiled binary; if Go is missing, the alias points to `python3 main.py`.
3. Verify Docker availability; if Docker is not running, the `RUN` tool will be disabled with a clear warning.

<!-- ES -->
## Instalación
```bash
# Clonar el repositorio
git clone https://github.com/your-org/anti-agent.git
cd anti-agent/Anti

# Instalar dependencias de Python (se recomienda virtualenv)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Compilar el binario Go (requiere Go 1.22+)
./install.sh
```
El instalador:
1. Compila el lanzador Go (`launcher.go`) en el ejecutable `anti`.
2. Crea un alias `anti` en `~/.bashrc` que ejecuta el binario; si Go no está presente, el alias apunta a `python3 main.py`.
3. Verifica la disponibilidad de Docker; si Docker no está activo, la herramienta `RUN` quedará deshabilitada con una advertencia clara.

---

<!-- EN -->
## Quick Start
### Web Dashboard
```bash
# Start the backend API (default port 8000)
python3 server.py &
# Open the dashboard in your browser
xdg-open http://localhost:8000
```
The dashboard displays provider status, model name, and real‑time telemetry.

### Terminal UI
```bash
anti           # launches the Bubble Tea TUI
```
Use the arrow keys to navigate the menu, `Enter` to select, and `Esc` to return.

<!-- ES -->
## Inicio Rápido
### Panel Web
```bash
# Iniciar la API backend (puerto 8000 por defecto)
python3 server.py &
# Abrir el panel en el navegador
xdg-open http://localhost:8000
```
El panel muestra el estado del proveedor, el nombre del modelo y telemetría en tiempo real.

### UI de Terminal
```bash
anti           # lanza la TUI de Bubble Tea
```
Utiliza las flechas para navegar, `Enter` para seleccionar y `Esc` para volver.

---

<!-- EN -->
## Configuration (`config.json`)
```json
{
  "agent_name": "Anti",
  "provider": "auto",
  "model": null,
  "lm_studio_url": "http://127.0.0.1:1234/v1",
  "ollama_url": "http://127.0.0.1:11434",
  "max_iterations": 10,
  "report_format": "markdown"
}
```
* `provider` can be `auto`, `lmstudio`, `ollama`, `openai`, `gemini`, `deepseek`, `anthropic`, `minimax`, or `openaicompatible`.
* When `provider` is `auto`, the system detects the first available local provider (LM Studio or Ollama).

<!-- ES -->
## Configuración (`config.json`)
```json
{
  "agent_name": "Anti",
  "provider": "auto",
  "model": null,
  "lm_studio_url": "http://127.0.0.1:1234/v1",
  "ollama_url": "http://127.0.0.1:11434",
  "max_iterations": 10,
  "report_format": "markdown"
}
```
* `provider` puede ser `auto`, `lmstudio`, `ollama`, `openai`, `gemini`, `deepseek`, `anthropic`, `minimax` u `openaicompatible`.
* Cuando `provider` es `auto`, el sistema detecta el primer proveedor local disponible (LM Studio o Ollama).

---

<!-- EN -->
## API Examples
### Health Check
```bash
curl http://localhost:8000/api/status
```
```json
{ "status": "ok", "provider": "ollama", "model": "llama2:7b" }
```

### Knowledge Graph Query
```bash
curl http://localhost:8000/api/knowledge_graph | jq '.'
```
```json
{
  "entities": [
    {"id":1,"type":"concept","value":"Anti‑Agent"},
    {"id":2,"type":"concept","value":"LLM"}
  ],
  "edges": [
    {"source":1,"target":2,"relation":"uses"}
  ]
}
```

<!-- ES -->
## Ejemplos de API
### Verificación de salud
```bash
curl http://localhost:8000/api/status
```
```json
{ "status": "ok", "provider": "ollama", "model": "llama2:7b" }
```

### Consulta del Grafo de Conocimiento
```bash
curl http://localhost:8000/api/knowledge_graph | jq '.'
```
```json
{
  "entities": [
    {"id":1,"type":"concept","value":"Anti‑Agent"},
    {"id":2,"type":"concept","value":"LLM"}
  ],
  "edges": [
    {"source":1,"target":2,"relation":"uses"}
  ]
}
```

---

<!-- EN -->
## Benchmarking Low‑Parameter Models
The repository includes a simple benchmark script `benchmark.sh` that measures throughput and token latency for a given model.
```bash
./benchmark.sh --provider ollama --model llama2:7b --prompt "Explain quantum tunneling in 2 sentences."
```
The script reports:
- **Tokens per second**
- **Average latency (ms)**
- **Memory usage**
Results should be uploaded to `docs/benchmarks/` as a markdown table.

<!-- ES -->
## Benchmarking de Modelos de Bajo Parámetro
El repositorio incluye un script sencillo de benchmark `benchmark.sh` que mide el rendimiento y latencia de tokens para un modelo dado.
```bash
./benchmark.sh --provider ollama --model llama2:7b --prompt "Explica el túnel cuántico en 2 frases."
```
El script informa:
- **Tokens por segundo**
- **Latencia media (ms)**
- **Uso de memoria**
Los resultados deben subirse a `docs/benchmarks/` como una tabla markdown.

---

<!-- EN -->
## Architecture Diagram
```mermaid
flowchart LR
    subgraph UI[User Interfaces]
        Web[Web Dashboard] --> API
        TUI[Terminal UI] --> API
    end
    API[FastAPI Backend] --> DockerSandbox[Docker Sandbox (RUN tool)]
    DockerSandbox --> DB[(SQLite DB)]
    DB --> KG[Knowledge Graph]
    subgraph Plugins[Plugin System]
        Plugins --> Tools[Tool Registry]
    end
    API --> Plugins
    Tools --> DB
```
The diagram shows the flow from UI components through the API, secure sandbox, and persistent storage.

<!-- ES -->
## Diagrama de Arquitectura
```mermaid
flowchart LR
    subgraph UI[Interfaces de Usuario]
        Web[Panel Web] --> API
        TUI[TUI de Terminal] --> API
    end
    API[Backend FastAPI] --> DockerSandbox[Sandbox Docker (herramienta RUN)]
    DockerSandbox --> DB[(Base de datos SQLite)]
    DB --> KG[Gráfico de Conocimientos]
    subgraph Plugins[Sistema de Plugins]
        Plugins --> Tools[Registro de Herramientas]
    end
    API --> Plugins
    Tools --> DB
```
El diagrama ilustra el flujo desde las interfaces de usuario, pasando por la API, el sandbox seguro y el almacenamiento persistente.

---

<!-- EN -->
## Security
All external command execution (`RUN` tool) is performed inside an isolated Docker container with:
- `--network=none`
- `--memory=512m`
- `--cpus=1.0`
- `--cap-drop=ALL`
If Docker is not available, the tool returns a clear error message and does not execute the command on the host.

<!-- ES -->
## Seguridad
Todas las ejecuciones de comandos externos (`RUN`) se realizan dentro de un contenedor Docker aislado con:
- `--network=none`
- `--memory=512m`
- `--cpus=1.0`
- `--cap-drop=ALL`
Si Docker no está disponible, la herramienta devuelve un mensaje de error claro y no ejecuta el comando en el host.

---

<!-- EN -->
## Extensibility (Plugins)
Place new plugins in `src/plugins/`. Each plugin must expose an `anti_tool` decorator. The system automatically registers the tool at startup.
```python
from src.plugin_manager import anti_tool

@anti_tool(name="MYTOOL", description="My custom tool")
def my_tool(raw_args: str):
    return f"You passed: {raw_args}"
```
After adding a plugin, restart the server or TUI to load it.

<!-- ES -->
## Extensibilidad (Plugins)
Coloca nuevos plugins en `src/plugins/`. Cada plugin debe exponer un decorador `anti_tool`. El sistema registra automáticamente la herramienta al iniciar.
```python
from src.plugin_manager import anti_tool

@anti_tool(name="MYTOOL", description="Mi herramienta personalizada")
def my_tool(raw_args: str):
    return f"Has pasado: {raw_args}"
```
Después de agregar un plugin, reinicia el servidor o la TUI para cargarlo.

---

<!-- EN -->
## Contributing
We follow the `branch‑pr` workflow. Create an issue first, then a branch, and open a pull request. CI will run all Go and Python tests before merging.

<!-- ES -->
## Contribuir
Seguimos el flujo de trabajo `branch‑pr`. Crea primero una *issue*, luego una rama y abre una *pull request*. CI ejecutará todas las pruebas de Go y Python antes de mezclar.

---

<!-- EN -->
## License
MIT © 2024–2026 Anti‑Agent developers.

<!-- ES -->
## Licencia
MIT © 2024–2026 desarrolladores de Anti‑Agent.

---

<!-- EN -->
## Screenshots
![Web UI Screenshot](/home/hunther4/.gemini/antigravity/brain/0b2a54c4-516e-455a-ad8f-e1418d623f52/screenshot_web_ui_1780095673416.png)

![TUI Screenshot](/home/hunther4/.gemini/antigravity/brain/0b2a54c4-516e-455a-ad8f-e1418d623f52/screenshot_tui_1780095691676.png)

<!-- ES -->
## Capturas de pantalla
![Captura de Web UI](/home/hunther4/.gemini/antigravity/brain/0b2a54c4-516e-455a-ad8f-e1418d623f52/screenshot_web_ui_1780095673416.png)

![Captura de TUI](/home/hunther4/.gemini/antigravity/brain/0b2a54c4-516e-455a-ad8f-e1418d623f52/screenshot_tui_1780095691676.png)

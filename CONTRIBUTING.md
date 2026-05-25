# Contribuyendo a Anti

Anti es un agente autónomo de DevOps y Auditoría de Seguridad. Usamos un flujo de trabajo estructurado para mantener la calidad del código y la estabilidad del sistema.

---

## Estructura del Proyecto

```
Anti/
├── anti                  # Binary compilado del TUI (Go → Bubble Tea)
├── main.py               # Entry point: CLI interactivo o MCP server
├── server.py             # API REST (FastAPI) para el dashboard web
├── launcher.go           # TUI en Go (Bubble Tea) — menú interactivo
├── launcher.py           # TUI legacy en Python — centro de control
├── config.json           # Configuración central del agente
├── requirements.txt      # Dependencias Python
├── go.mod / go.sum       # Dependencias Go
├── install.sh            # Script de instalación automatizada
├── setup-keys.sh         # Configuración de API keys
├── src/                  # Código fuente Python del agente
│   ├── agent.py          # AntiAgent — orquestador principal
│   ├── brain.py          # Interfaz con el LLM
│   ├── memory.py         # MemoryManager — memoria persistente
│   ├── archive.py        # ArchiveManager — SQLite cold path + FTS5 + KG
│   ├── context_manager.py # ContextManager — ventana deslizante + integridad
│   ├── compactor.py      # HybridCompactor — compactación de contexto
│   ├── scorer.py         # PRM Scorer — evaluador de calidad de respuestas
│   ├── evolver.py        # SkillEvolver — evolución autónoma de habilidades
│   ├── consolidator.py   # MemoryConsolidator — mantenimiento de memoria
│   ├── tools.py          # Herramientas base (search, fetch, run, etc.)
│   ├── plugin_manager.py # PluginManager — registro y ejecución de plugins
│   ├── skills.py         # SkillManager — habilidades conductuales
│   ├── document_parser.py# Parser de documentos (PDF, texto, chunks)
│   ├── mcp_server.py     # MCP server mode (JSON-RPC stdin/stdout)
│   ├── providers/        # Adaptadores para proveedores de LLM
│   │   ├── base.py       # BaseProvider + ProviderFactory (abstracta)
│   │   ├── lmstudio.py   # LM Studio (local, OpenAI-compatible)
│   │   ├── ollama.py     # Ollama
│   │   ├── openai.py     # OpenAI
│   │   ├── gemini.py     # Google Gemini
│   │   ├── anthropic.py  # Anthropic Claude
│   │   ├── deepseek.py   # DeepSeek
│   │   ├── minimax.py    # MiniMax
│   │   └── openaicompatible.py # OpenAI Compatible (Groq, Together, etc.)
│   └── plugins/          # Plugins dinámicos registrados con @anti_tool
│       ├── core_tools.py # SEARCH, RUN, WRITE, READ, FETCH, RESEARCH
│       ├── web_reader.py # WEB_READ — scraper web a Markdown
│       ├── ast_security_auditor.py # AST_AUDIT — auditoría de seguridad
│       └── github_diff_auditor.py # DIFF_AUDIT — auditoría de PRs
├── memory/               # Datos persistentes del agente
│   ├── cold_archive.db   # SQLite FTS5 — archivo frío de engrams
│   ├── engrams/          # Engrams en JSON (hot path)
│   ├── skills/           # Habilidades conductuales (MCPs instalados)
│   ├── logs.jsonl        # Logs de experiencia
│   └── patterns.md       # Patrones y lecciones aprendidas
├── workspace/            # Área de trabajo del agente
├── prompts/              # Templates de prompts del sistema
├── docs/                 # Documentación técnica
├── lectura/              # Documentos cargados vía @mention
├── extras/               # Archivos auxiliares
│   ├── web/              # Dashboard web (HTML/CSS/JS)
│   ├── server.py         # API server (copia independiente)
│   └── searxng/          # Config Docker para SearxNG
├── tests/                # Tests unitarios y de integración
└── logs/                 # Logs de ejecución
```

---

## Configuración del Entorno de Desarrollo

### Requisitos

- **Python 3.10+**
- **Go 1.20+** (solo para compilar el TUI)
- **Docker** (para el sandbox de ejecución de comandos)
- **LM Studio** o **Ollama** (para modo local)
- **SearxNG** (opcional, para búsqueda web local)

### Setup Rápido

```bash
git clone --recursive https://github.com/Hunther4/Anti.git
cd Anti
./install.sh
source ~/.bashrc
```

### Setup Manual

```bash
# Python virtual env
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Compilar TUI (opcional)
go build -o anti launcher.go

# Configurar API keys (opcional, para modo cloud)
cp .env.example .env
# Editar .env con tus claves
```

### SearxNG (opcional)

```bash
cd extras/searxng
docker compose up -d
# SearxNG disponible en http://localhost:8080
```

---

## Flujo de Trabajo con Git

### Ramas

- `main` — estable, lista para producción
- `develop` — integración de características
- `feature/<nombre>` — características nuevas
- `fix/<nombre>` — correcciones de bugs
- `release/<version>` — preparación de release

### Commits

Usamos **Conventional Commits**:

```
feat: nueva característica
fix: corrección de bug
docs: documentación
refactor: refactorización sin cambio funcional
perf: mejora de rendimiento
test: tests
chore: tareas de mantenimiento
style: formato, estilos
```

No incluyas atribuciones de IA (Co-Authored-By) en los commits.

### Pull Requests

1. Asegurate de que el código pase los tests existentes.
2. Si agregás funcionalidad, incluí tests.
3. Mantené los PRs enfocados en un solo cambio.
4. La descripción debe explicar QUÉ y POR QUÉ, no CÓMO.
5. Enlazá el issue correspondiente si existe.

---

## Estándares de Código

### Python

- Type hints obligatorios en funciones públicas.
- Docstrings en español o inglés (consistente con el archivo).
- Máximo 100 caracteres por línea (apuntá a 88).
- Nombres de variables/clases/funciones en inglés.
- Usá `logging` en vez de `print` para logs del sistema.
- Excepciones: capturá errores específicos, no `Exception` genérico.

### Go (TUI)

- Seguí las convenciones estándar de Go (`gofmt`).
- Usá `lipgloss` para estilos y `bubbletea` para el modelo TUI.
- Mantené el TUI como una capa delgada: toda la lógica pesada va en Python.

### Plugins

- Cada plugin es un archivo `.py` en `src/plugins/`.
- Registrá herramientas con el decorador `@anti_tool(name, description)`.
- La función puede ser síncrona o asíncrona (el `PluginManager` maneja ambos casos).
- La description debe ser clara para que el LLM entienda cuándo usarla.

---

## Tests

```bash
# Activar el venv y correr tests
source venv/bin/activate
python -m pytest tests/ -v

# Tests específicos
python -m pytest tests/test_security_auditor.py -v
```

---

## Arquitectura General

```
Usuario → TUI (Go/Python) → AntiAgent (Python)
  → Provider (LLM) → ReAct Loop → PluginManager
  → MemoryManager → SQLite FTS5 + Engrams
  → PRM Scorer → Respuesta Final
```

El TUI (Go con Bubble Tea o Python) lanza `main.py` que instancia `AntiAgent`. El agente selecciona un provider (auto-detectado o configurado), ejecuta un loop ReAct (máximo 10 iteraciones) donde el LLM decide qué herramientas/plugins invocar, y al final evalúa la calidad de la respuesta con el PRM Scorer antes de devolverla.

---

## Agregar un Nuevo Provider

1. Crear `src/providers/minuevo.py` heredando de `BaseProvider`.
2. Implementar `chat()`, `list_models()`, `sync_model_context()`, `get_context_info()`, `check_connection()`.
3. Agregar el provider en `ProviderFactory.PROVIDERS` y su import lazy en `ProviderFactory.create()`.
4. Agregar la URL/API key en `launcher.go` (struct `Config`) y en `launcher.py`.
5. Documentar en `docs/config.md` y `docs/architecture.md`.

---

## Agregar un Plugin

Ver [`docs/plugins.md`](docs/plugins.md) para la guía detallada.

---

## Reportar Issues

- Incluí la versión de Anti (`git log --oneline -1`).
- Incluí el provider y modelo que estabas usando.
- Incluí el log de error completo.
- Describí los pasos para reproducir.

---

## Licencia

MIT — ver [`LICENSE`](LICENSE).

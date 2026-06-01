<p align="center">
  <img src="https://img.shields.io/badge/version-1.6 Quantum-blueviolet?style=for-the-badge" alt="Version">
  <img src="https://img.shields.io/badge/python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/go-1.22+-00ADD8?style=for-the-badge&logo=go&logoColor=white" alt="Go">
  <img src="https://img.shields.io/badge/license-MIT-green?style=for-the-badge" alt="License">
  <img src="https://img.shields.io/badge/platform-linux%20%7C%20macos-lightgrey?style=for-the-badge" alt="Platform">
</p>

<h1 align="center">Anti-Agent</h1>

<p align="center">
  <strong>Autonomous AI agent with persistent memory, sandboxed execution, and multi-provider support.</strong><br>
  <em>Built for local LLMs. Designed to evolve.</em>
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> •
  <a href="#features">Features</a> •
  <a href="#configuration">Configuration</a> •
  <a href="#commands--interface">Commands</a> •
  <a href="#architecture">Architecture</a> •
  <a href="#api-reference">API</a> •
  <a href="#contributing">Contributing</a>
</p>

---

## What is Anti-Agent?

Anti-Agent is a self-evolving AI assistant that runs **entirely on your machine**. It connects to local LLMs (LM Studio, Ollama) or cloud providers (OpenAI, Gemini, Anthropic), remembers everything through a persistent memory system, and executes commands safely inside Docker sandboxes.

**Key differentiator**: Anti doesn't just answer questions — it **learns from every interaction**, stores knowledge as structured engrams, and evolves its own skills over time.

```
You: "What did we fix yesterday?"
Anti: "Yesterday we fixed 3 critical bugs in the provider system:
       1. Ollama context length scaling was inverted (8GB > 4GB check was backwards)
       2. LM Studio returned garbage instead of raising ConnectionError
       3. HTTP sessions leaked because close() was never called on retry"
```

---

## Features

### Multi-Provider LLM Support
Connect to any LLM backend — local or cloud:

| Provider | Type | Default URL |
|----------|------|-------------|
| LM Studio | Local | `http://127.0.0.1:1234/v1` |
| Ollama | Local | `http://127.0.0.1:11434` |
| OpenAI | Cloud | Requires API key |
| Gemini | Cloud | Requires API key |
| Anthropic | Cloud | Requires API key |
| DeepSeek | Cloud | Requires API key |
| Minimax | Cloud | Requires API key |
| OpenAI-compatible | Any | Custom URL |

Set `"provider": "auto"` in `config.json` and Anti auto-detects the first available backend.

### Persistent Memory (Engrams)
Every conversation, decision, and discovery is stored as structured **engrams** in SQLite with FTS5 full-text search:

```bash
# Search memory from the CLI
anti --mem-search "provider bugs"

# Bootstrap memory on startup
anti --mem-init
```

Memory features:
- **FTS5 full-text search** across all stored knowledge
- **Knowledge graph** with entities and relationships
- **Automatic decay** — old, unused memories lose relevance over time
- **Consolidation** — related engrams merge automatically

### Sandboxed Execution
All command execution happens inside isolated Docker containers:

```yaml
# Security flags applied to every sandbox:
--network=none        # No network access
--memory=512m         # Memory limit
--cpus=1.0            # CPU limit
--cap-drop=ALL        # Drop all Linux capabilities
```

If Docker isn't available, execution is **disabled** with a clear warning — never falls back to host execution.

### Autonomous Evolution
Anti learns from its mistakes:

1. **PRM Scorer** — Every response is evaluated by a Process Reward Model
2. **Skill Evolver** — Failed tasks trigger automatic skill analysis
3. **Memory Consolidator** — Related engrams merge to reduce noise
4. **Context Manager** — Smart compaction preserves important context

### Plugin System
Extend Anti with custom tools:

```python
# src/plugins/my_tool.py
from src.plugin_manager import anti_tool

@anti_tool(name="MYTOOL", description="Does something useful")
def my_tool(raw_args: str) -> str:
    # Your logic here
    return f"Result: {processed_data}"
```

Restart the TUI or server to load new plugins.

### Dual Interface
- **TUI (Terminal UI)** — Cyberpunk-styled Bubble Tea interface (`./anti`)
- **Web Dashboard** — Real-time monitoring at `http://localhost:8000`
- **CLI Mode** — Direct terminal interaction (`python3 main.py`)

---

## Quick Start

### Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.10+ | With pip and venv |
| Go | 1.22+ | Only for TUI compilation |
| Docker | 20.10+ | Optional, for sandboxed execution |
| LM Studio or Ollama | Latest | For local LLM inference |

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/Hunther4/Anti.git
cd Anti

# 2. Create virtual environment and install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Compile the Go TUI (optional but recommended)
./install.sh

# 4. Start a local LLM (pick one)
# Option A: LM Studio — load any model, start the server on port 1234
# Option B: Ollama — pull a model and serve
ollama pull llama3
ollama serve
```

### First Run

```bash
# Launch the TUI
./anti

# Or run in CLI mode
python3 main.py
```

Anti auto-detects your running LLM backend and connects.

### Configuration

Create or edit `config.json` in the project root:

```json
{
  "agent_name": "Anti",
  "provider": "auto",
  "model": null,
  "lm_studio_url": "http://127.0.0.1:1234/v1",
  "ollama_url": "http://127.0.0.1:11434",
  "openai_api_key": "sk-...",
  "gemini_api_key": "...",
  "anthropic_api_key": "sk-ant-...",
  "max_iterations": 10,
  "timeout": 120,
  "enable_prm_scorer": true,
  "auto_reflect": true,
  "history_limit": 50,
  "report_format": "markdown"
}
```

**Key options:**

| Field | Type | Description |
|-------|------|-------------|
| `provider` | `"auto"` / provider name | LLM backend selection |
| `model` | `null` / string | Model name override (null = auto-detect) |
| `enable_prm_scorer` | `bool` | Enable response quality scoring |
| `auto_reflect` | `bool` | Auto-reflect on low-quality responses |
| `timeout` | `int` | HTTP timeout in seconds |
| `max_iterations` | `int` | Max tool-call iterations per turn |

See [`docs/config.md`](docs/config.md) for the full configuration reference.

---

## Commands & Interface

### TUI Navigation

| Key | Action |
|-----|--------|
| `↑` / `↓` | Navigate menu |
| `Enter` | Select option |
| `Esc` | Go back |
| `Ctrl+C` | Exit |

### CLI Commands

Type these directly in the Anti CLI prompt:

| Command | Description |
|---------|-------------|
| `help` | Show all available commands |
| `exit` / `quit` | Exit the agent |
| `/status` | Show provider, model, and memory stats |
| `/memory` | Search persistent memory |
| `/tools` | List available tools and plugins |
| `/evolve` | Trigger skill evolution manually |
| `/compact` | Force context compaction |
| `/history` | Show conversation history |
| `/config` | Show current configuration |
| `/reset` | Reset conversation context |

### Tool Calls (Automatic)

When you ask Anti to do something, it automatically selects the right tool:

```
You: "Search for the latest Python 3.13 release notes"
Anti: [Calls SEARCH tool → fetches results → summarizes]

You: "Read the file config.json"
Anti: [Calls READ tool → returns file contents]

You: "Run the tests"
Anti: [Calls RUN tool → executes in Docker sandbox → returns output]
```

### Available Tools

| Tool | Description | Sandbox |
|------|-------------|---------|
| `SEARCH` | Web search via DuckDuckGo/SearXNG | No |
| `WEB_READ` | Fetch and extract text from URLs | No |
| `READ` | Read files from workspace | No |
| `WRITE` | Write files to workspace | No |
| `RUN` | Execute shell commands | **Yes (Docker)** |
| `RESEARCH` | Autonomous multi-source research | No |
| `AST_AUDIT` | Security audit via AST parsing | No |
| `DIFF_AUDIT` | Code diff analysis | No |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    User Interfaces                       │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   TUI    │  │ Web Dashboard│  │   CLI / Python   │  │
│  │ (Go/Bubble)│ │  (HTML/CSS)  │  │    (main.py)     │  │
│  └────┬─────┘  └──────┬───────┘  └────────┬─────────┘  │
│       │               │                    │             │
│       └───────────────┼────────────────────┘             │
│                       ▼                                  │
│  ┌─────────────────────────────────────────────────┐    │
│  │              AntiAgent (agent.py)                │    │
│  │  Orchestrates: LLM calls, tool routing, memory   │    │
│  └──────────┬──────────┬──────────┬────────────────┘    │
│             │          │          │                      │
│     ┌───────▼──┐  ┌────▼────┐  ┌─▼──────────────┐     │
│     │  Brain   │  │ Memory  │  │  Plugin System  │     │
│     │ (httpx)  │  │(SQLite) │  │  (tool loader)  │     │
│     └──────┬───┘  └────┬────┘  └────────┬────────┘     │
│            │           │                 │               │
│     ┌──────▼───┐  ┌────▼────┐  ┌────────▼────────┐     │
│     │Providers │  │ Archive │  │     Tools        │     │
│     │ LM/OA/G  │  │ (FTS5+  │  │ Search/FS/Run/  │     │
│     │ /Anth/etc│  │  KG)    │  │ Browser/Network  │     │
│     └──────────┘  └─────────┘  └─────────────────┘     │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │              Autonomous Layer                     │   │
│  │  PRM Scorer → Skill Evolver → Memory Consolidator │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### Key Components

| Component | File | Role |
|-----------|------|------|
| **Brain** | `src/brain.py` | LLM communication via httpx (async) |
| **Providers** | `src/providers/` | Multi-backend adapters (8 providers) |
| **Agent** | `src/agent.py` | Main orchestrator, ReAct loop, tool routing |
| **Memory** | `src/memory.py` | Persistent JSON-based engram storage |
| **Archive** | `src/archive.py` | SQLite FTS5 + Knowledge Graph (aiosqlite) |
| **Scorer** | `src/scorer.py` | PRM response quality evaluation |
| **Evolver** | `src/evolver.py` | Autonomous skill evolution |
| **Compactor** | `src/compactor.py` | Context window management |
| **Plugins** | `src/plugins/` | Dynamic tool registration |
| **TUI** | `cmd/tui/` | Go Bubble Tea terminal interface |
| **Web** | `extras/web/` | HTML/CSS dashboard |

---

## API Reference

### Health Check
```bash
curl http://localhost:8000/api/status
```
```json
{
  "status": "ok",
  "provider": "ollama",
  "model": "llama3:8b",
  "version": "1.6"
}
```

### Chat
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the capital of France?"}'
```

### Knowledge Graph
```bash
# Query all entities
curl http://localhost:8000/api/knowledge_graph | jq '.'

# Query by type
curl "http://localhost:8000/api/knowledge_graph?type=concept" | jq '.'
```

### Memory Search
```bash
curl -X POST http://localhost:8000/api/memory/search \
  -H "Content-Type: application/json" \
  -d '{"query": "provider architecture", "limit": 10}'
```

### Memory Stats
```bash
curl http://localhost:8000/api/memory/stats
```
```json
{
  "total_engrams": 156,
  "total_relations": 42,
  "db_size_kb": 2048,
  "oldest_engram": "2024-01-15",
  "newest_engram": "2026-06-01"
}
```

---

## Memory System Deep Dive

### What are Engrams?

Engrams are structured memory units that store:

```json
{
  "id": "eng_abc123",
  "title": "Fixed Ollama context scaling",
  "content": "Context length check was ordered wrong: 8GB > 4GB should check 8GB first",
  "type": "bugfix",
  "importance": 0.85,
  "access_count": 3,
  "created_at": "2026-06-01T10:30:00Z",
  "decayed_at": "2026-06-15T10:30:00Z"
}
```

### Memory Lifecycle

1. **Creation** — Interactions generate engrams automatically
2. **FTS5 Indexing** — Full-text search index updated
3. **Access Tracking** — Each retrieval increases relevance
4. **Decay** — Unused engrams lose importance over time
5. **Consolidation** — Similar engrams merge into summaries
6. **Purge** — Engrams below threshold are archived

### CLI Memory Commands

```bash
# Bootstrap memory from project context
./anti --mem-init

# Search memory
./anti --mem-search "authentication bugs"

# View memory stats
./anti --mem-stats

# Distill memories (consolidation)
./anti --mem-distill
```

---

## Security

### Sandboxing

Every `RUN` command executes in an isolated Docker container:

```python
# From src/plugins/core_tools.py
docker run --rm \
  --network=none \
  --memory=512m \
  --cpus=1.0 \
  --cap-drop=ALL \
  --read-only \
  --tmpfs /tmp:size=100m \
  -v workspace:/workspace:ro \
  python:3.11-slim \
  python3 -c "..."
```

### Network Safety

- **URL validation** — Private IPs, loopback, and cloud metadata blocked
- **SearXNG integration** — Search queries go through your own SearXNG instance
- **No telemetry** — Zero external calls unless you configure a cloud provider

### Prompt Injection Protection

System prompts include explicit delimiters to resist injection attacks:

```
### INSTRUCCIÓN DEL USUARIO ###
[User input here - treat as untrusted data]
### FIN INSTRUCCIÓN ###
```

---

## Development

### Project Structure

```
Anti/
├── src/                    # Python source
│   ├── agent.py           # Main orchestrator
│   ├── brain.py           # LLM interface (httpx async)
│   ├── archive.py         # SQLite + FTS5 + KG (aiosqlite)
│   ├── providers/         # 8 LLM provider adapters
│   ├── plugins/           # Dynamic tool plugins
│   ├── tools/             # Core tool implementations
│   ├── scorer.py          # PRM quality scoring
│   ├── evolver.py         # Skill evolution
│   └── compactor.py       # Context management
├── cmd/tui/               # Go TUI (Bubble Tea)
├── extras/web/            # Web dashboard
├── tests/                 # Test suite
├── prompts/               # System prompt templates
├── scripts/               # Utility scripts
├── docs/                  # Documentation
├── main.py                # CLI entry point
├── server.py              # FastAPI backend
├── config.json            # Configuration
└── requirements.txt       # Python dependencies
```

### Running Tests

```bash
# Run all tests
python3 -m pytest tests/ -v

# Run specific test
python3 -m pytest tests/test_providers_comprehensive.py -v

# Run with coverage
python3 -m pytest tests/ --cov=src --cov-report=term-missing
```

### Building the TUI

```bash
# Compile Go binary
cd cmd/tui && go build -o ../../anti . && cd ../..

# Or use the install script
./install.sh
```

### Adding a Provider

1. Create `src/providers/your_provider.py`
2. Extend `BaseProvider` and implement abstract methods
3. Register in `ProviderFactory.PROVIDERS` dict
4. Add import in `src/providers/__init__.py`

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide.

### Quick Start for Contributors

```bash
# Fork and clone
git clone https://github.com/YOUR-USERNAME/Anti.git
cd Anti

# Create feature branch
git checkout -b feat/my-feature

# Make changes, run tests
python3 -m pytest tests/ -v

# Commit with conventional format
git commit -m "feat: add new provider for X"

# Push and create PR
git push origin feat/my-feature
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contribution guidelines |
| [docs/architecture.md](docs/architecture.md) | Detailed architecture docs |
| [docs/config.md](docs/config.md) | Full configuration reference |
| [docs/plugins.md](docs/plugins.md) | Plugin development guide |
| [docs/troubleshooting.md](docs/troubleshooting.md) | Common issues and fixes |
| [LICENSE](LICENSE) | MIT License |

---

## License

MIT © 2024–2026 Anti-Agent developers.

---

<p align="center">
  <em>Built with care for the local AI community.</em><br>
  <strong>If you run it, it learns. If you teach it, it evolves.</strong>
</p>

# Anti — Autonomous DevOps & Security Auditor Agent (v1.0 Cosmic) 🚀

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Sandboxed-blue.svg)](https://www.docker.com/)

Anti is an autonomous, self-evolving DevOps and Security Auditor Agent designed for secure, local-first execution with unified SQLite memory and plug-and-play dynamic extensibility.

---

## ⚡ Quick Start

```bash
# Clone the repository and submodules
git clone --recursive https://github.com/Hunther4/Anti.git
cd Anti

# Quick installation (creates venv, installs deps, and adds 'anti' alias)
chmod +x install.sh
./install.sh
source ~/.bashrc

# Run the agent via the Control Menu
anti
```

---

## 🛠️ Cosmic Architecture (v1.0)

Anti has evolved from a standard ReAct conversational assistant into an extensible, fully sandboxed auditing platform.

```text
Anti/
├── src/
│   ├── plugins/        # 🔌 Plug & Play Dynamic Python Plugins
│   │   ├── core_tools.py
│   │   ├── ast_security_auditor.py
│   │   └── github_diff_auditor.py
│   ├── plugin_manager.py# Dynamic import & registry logic
│   ├── agent.py        # Generic decoupled ReAct Loop
│   ├── archive.py      # Unified SQLite Knowledge Graph & FTS5 search
│   └── memory.py       # Memory persistence layer
├── memory/
│   └── cold_archive.db # Single source of truth (SQLite)
├── workspace/          # Sandboxed working directory
└── tests/              # Unit test suites
```

### 1. Unified SQLite FTS5 Memory Engine
- **Single Source of Truth**: Multi-file JSON memory is deprecated. All Engrams, structural entities, logs, and relationships are stored in `memory/cold_archive.db`.
- **Full-Text Search (FTS5)**: Integrated native SQLite virtual tables and real-time triggers (`engram_ai`, `engram_ad`, `engram_au`) to achieve sub-millisecond keyword and semantic search queries over thousands of memory records.

### 2. Plug & Play Dynamic Python Plugins
- **Decoupled ReAct Loop**: No more hardcoded tool chains or endless `if/elif` blocks in `agent.py`. The agent matches `[TOOL_NAME: arguments]` patterns dynamically.
- **Dynamic Imports**: Any Python script dropped inside `src/plugins/` using the `@anti_tool` decorator automatically exposes its capabilities to the LLM's system prompt on startup.

### 3. Docker Sandboxing & Execution Security
- **Command Sandboxing**: Shell commands run inside an isolated `python:3.12-slim` Docker container. The local workspace directory is mounted safely.
- **Local Fallback Policies**: In case Docker is unavailable, a strict security policy filters chaining operators (`&&`, `;`, `||`, etc.) and blacklisted commands.

---

## 🔌 Standard Auditing Toolkit (New Plugins)

### 🛡️ AST Python Security Auditor (`AST_AUDIT`)
Uses Python's native Abstract Syntax Tree (`ast`) to perform deep structural analysis of Python codebases in milliseconds:
- Detects unsafe executions (`eval()`, `exec()`, `os.system()`).
- High-entropy secrets and hardcoded password scanning.
- Empty exception handling suppressions (`except: pass`).

### 🐙 PR & Diff Auditor (`DIFF_AUDIT`)
Designed to inspect pending changes and Pull Requests for vulnerabilities:
- Downloads raw patches/diffs dynamically from GitHub PR links.
- Scans newly added lines (`+`) for secrets, shell command injections, and bad security practices.

---

## 🤝 CLI Command Reference

| Command | Description |
|:--------|:-----------|
| `status` | System integrity matrix, Docker daemon, and SQLite memory checks |
| `reflect` | Triggers a Dual Evolution cycle, compacting engrams and updating behavioral skills |
| `consolidate` | Triggers background memory maintenance (merging entity nodes and pruning decay) |
| `reasoner` | Toggles dynamic self-critique reasoning layer for complex debugging |

---

## 🤝 Contributing

We follow a strict **issue-first** workflow. Please open a discussion issue before submitting a PR.

1. Fork the repository.
2. Create your feature branch (`git checkout -b feature/MyAwesomePlugin`).
3. Decorate your tool using `@anti_tool` inside `src/plugins/`.
4. Run tests: `python3 -m unittest discover tests/`
5. Open a Pull Request.

---

# Anti — Agente de Auditoría de Seguridad & DevOps (v1.0 Cósmico) 🇪🇸

Anti es un agente de DevOps y Auditoría de Seguridad autónomo, diseñado para ejecución segura local, persistencia unificada en base de datos SQLite y extensibilidad dinámica "Plug and Play".

## 🛠️ Arquitectura Cósmica
- **Memoria Unificada SQLite FTS5**: Deprecamos la persistencia en múltiples JSONs. Toda la memoria se archiva en una base de datos central de alto rendimiento utilizando índices inversos FTS5.
- **Plugins Dinámicos**: Olvidate de modificar el core del agente. Decorá cualquier función con `@anti_tool` dentro de `/src/plugins/` y Anti aprenderá a usarla de inmediato.
- **Auditoría AST y de Diffs**: Equipado de fábrica con escáneres estáticos de código (`AST_AUDIT`) e inspectores automatizados de Pull Requests (`DIFF_AUDIT`).

---
**Hunther4** — *Autonomous Evolving Systems*

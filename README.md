# Anti — Autonomous DevOps & Security Auditor Agent (v1.5 Cosmic) 🚀

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Go](https://img.shields.io/badge/Go-1.20+-00ADD8.svg)](https://go.dev/)
[![Docker](https://img.shields.io/badge/Docker-Sandboxed-blue.svg)](https://www.docker.com/)

Anti is an autonomous, self-evolving DevOps and Security Auditor Agent designed for secure, local-first execution with unified SQLite FTS5 memory, plug-and-play dynamic extensibility, and highly optimized, provider-aware context windows.

---

## 💡 Architecture & Execution Flow

```mermaid
graph TD
    User([Usuario]) -->|Pregunta / Comando| TUI[TUI: launcher.go]
    TUI -->|Invocación Async| Agent[AntiAgent: agent.py]
    Agent -->|1. Obtiene Memoria Latente| Memory[(SQLite Engine: cold_archive.db)]
    Agent -->|2. Gestión de Ventana Deslizante| ContextMgr[ContextManager]
    ContextMgr -->|Local: 10 msgs | LLM[Local LLM / LM Studio / Ollama]
    ContextMgr -->|Nube: 100 msgs| CloudLLM[Cloud LLM / Gemini / Claude]
    LLM & CloudLLM -->|3. Loop de Pensamiento ReAct| PluginMgr[PluginManager]
    PluginMgr -->|Llama Plugins| Tools[AST_AUDIT / WEB_READ / DIFF_AUDIT]
    Tools -->|Resultados de Herramienta| Agent
    Agent -->|4. PRM Scorer (50 tokens max)| LLMJudge[LLM Juez Quality Check]
    LLMJudge -->|Score >= 0.7| Agent
    Agent -->|Respuesta Final Destilada| TUI
```

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

## 🔌 Core Auditing & Web Toolkit (Plugins)

### 🛡️ AST Python Security Auditor (`AST_AUDIT`)
Uses Python's native Abstract Syntax Tree (`ast`) to perform deep structural analysis of Python codebases in milliseconds:
- Detects unsafe executions (`eval()`, `exec()`, `os.system()`).
- High-entropy secrets and hardcoded password scanning.
- Empty exception handling suppressions (`except: pass`).

### 🌐 Clean Web Content Scraper (`WEB_READ`) [NEW ⚡]
A highly resilient Web Scraper designed to extract pure factual data from any website:
- **Boilerplate Stripper**: Bypasses ads, headers, footers, and scripts using BeautifulSoup.
- **Markdown Conversion**: Delivers ultra-clean, structured Markdown to save massive prompt context.
- **Anti-Bot Bypass**: Randomized headers simulating real browsers.

### 🐙 PR & Diff Auditor (`DIFF_AUDIT`)
Designed to inspect pending changes and Pull Requests for vulnerabilities:
- Downloads raw patches/diffs dynamically from GitHub PR links.
- Scans newly added lines (`+`) for secrets, command injections, and bad security practices.

---

## 🧠 Smart Context & Local-First Optimization

Anti incorporates state-of-the-art engineering to keep local models (like 35B MoE) extremely fast while unlocking full long-context reasoning for cloud APIs:

### 1. Provider-Aware Sliding Window (`max_history_len`)
- **Local Mode (LM Studio, Ollama)**: Dynamic history window is restricted to **10 messages (5 turns)**. Keeps prompt tokens small, saves VRAM, and achieves lightning-fast local generation.
- **Cloud Mode (Claude, Gemini, OpenAI)**: Expands history automatically to **100 messages (50 turns)**, leveraging 1M+ token context windows to solve complex, multi-layered auditing tasks.

### 2. Process Reward Model Scorer (PRM)
- Evaluates response quality in real-time.
- **Latence-Zero Optimization**: Prompt instructions are restricted to output only the rating tag (`Score: 1/0/-1`) with a strict maximum limit of **50 tokens**, completely eliminating thinking/reasoning overhead during evaluation.
- Toggleable via `"enable_prm_scorer"` in `config.json` for ultimate direct execution speed.

---

## 🔌 9 Supported AI Providers Matrix

Anti features native configuration support for every modern AI ecosystem:

| Provider | Type | API Key Config | Primary Models |
| :--- | :---: | :---: | :--- |
| **LM Studio** | Local | *None* | `Qwen 2.5 35B MoE`, `Llama 3 8B` |
| **Ollama** | Local | *None* | `mistral`, `codellama`, `deepseek-coder` |
| **OpenAI** | Cloud | `OpenAI Key` | `gpt-4o`, `gpt-4-turbo` |
| **Gemini (Google)** | Cloud | `Gemini Key` | `gemini-1.5-pro`, `gemini-1.5-flash` |
| **Claude (Anthropic)** | Cloud | `Anthropic Key` | `claude-3-5-sonnet`, `claude-3-haiku` |
| **DeepSeek** | Cloud | `DeepSeek Key` | `deepseek-chat`, `deepseek-coder` |
| **Minimax** | Cloud | `Minimax Key` | `abab6.5g-chat` |
| **OpenAI Compatible** | Hybrid | `OpenAI Comp Key` | *Custom / Groq / Together AI* |

---

## 🤝 CLI Command Reference

| Command | Description |
| :--- | :--- |
| `status` | System integrity matrix, Docker daemon, and SQLite memory checks |
| `reflect` | Triggers a Dual Evolution cycle, compacting engrams and updating behavioral skills |
| `consolidate` | Triggers background memory maintenance (merging entity nodes and pruning decay) |
| `reasoner` | Toggles dynamic self-critique reasoning layer for complex debugging |

---

# Anti — Agente de Auditoría de Seguridad & DevOps (v1.5 Cósmico) 🇪🇸

Anti es un agente de DevOps y Auditoría de Seguridad autónomo, diseñado para ejecución segura local, persistencia unificada en base de datos SQLite y optimización de contexto inteligente basada en proveedor.

### 🚀 Características Clave:
- **Lector Web Inteligente (`WEB_READ`)**: Extrae contenido web destilado en Markdown eliminando headers, footers y publicidad para no desperdiciar tokens.
- **Historial Adaptativo**: Ventana deslizante de 10 mensajes en local para velocidad óptima de GPU, y 100 mensajes en la nube para máxima profundidad cognitiva.
- **Memoria SQLite FTS5**: Búsquedas factuales ultra rápidas sobre la base de datos `cold_archive.db`.

---
**Hunther4** — *Autonomous Evolving Systems*

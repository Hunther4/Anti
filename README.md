# Anti — Autonomous Agent with Persistent Memory (v0.6) 🇺🇸

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)

Anti is an autonomous evolving agent designed for local-first execution with true persistent memory. Unlike standard agents that reset every session, Anti extracts knowledge (Engrams) and refines its own behavioral rules (Skills) through a continuous evolution cycle.

---

## ⚡ Quick Start

```bash
# Clone the repository and submodules
git clone --recursive https://github.com/Hunther4/Anti.git
cd Anti

# Setup virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# (Optional) Setup API keys for cloud providers
chmod +x setup-keys.sh
./setup-keys.sh  # Or create a .env file

# Run the agent
python main.py
```

---

## 🛠️ Architecture: The v0.6 Sentinel Core

The current version implements a modular architecture optimized for high-density tool use and long-term retention.

- **Brain**: Multi-provider inference engine with dynamic context management.
- **Memory**: Dual-layer system (Factual Engrams + Behavioral Skills).
- **Tools**: ReAct loop with "Wave Strategy" search and mandatory citation extraction.
- **Submodules**: Includes `agent-search` for deep, multi-threaded web research.

### Persistent Memory System
- **Engrams**: JSON-based factual knowledge extracted from successful interactions.
- **Skills**: Markdown-based behavioral rules (`SKILL.md`) that override default behavior.
- **Evolution**: The `reflect` command triggers a Dual Evolution cycle, synthesizing new patterns from recent logs.

---

## 🔌 Supported Providers

| Provider | Port | API Key | Auto-detect |
|:---------|:-------|:-------|:----------:|
| LM Studio | 1234 | No | Yes |
| Ollama | 11434 | No | Yes |
| OpenAI | cloud | Yes | No |
| Gemini | cloud | Yes | No |

### Performance Recommendation
For optimal tool execution and JSON parsing, we recommend **Llama 3.3 8B** (Dolphin/Abliterated) or **Qwen 2.5 Coder**.

---

## 🛠️ CLI Command Reference

| Command | Description |
|:--------|:-----------|
| `status` | System integrity matrix and connection status |
| `reflect` | Force Dual Evolution cycle (extract Engrams + refine Skills) |
| `consolidate` | Autonomous maintenance: purge decay data and merge redundant clusters |
| `search <query>`| Force a web search using the "Ola" strategy |
| `mcp list` | List installed Model Context Protocol tools |
| `benchmark` | Run the Sentinel Gauntlet (TPS, Latency, Agency, Persona) |
| `reasoner` | Toggle self-critique mode for higher accuracy |

---

## 📂 Project Structure

```text
Anti/
├── src/                # Core logic (Agent, Brain, Memory, Tools)
├── memory/             # Persistent storage
│   ├── engrams/        # Factual knowledge (JSON)
│   └── skills/         # Behavior skills (SKILL.md)
├── agent-search/       # Deep search submodule
├── workspace/          # Working directory for agent files
├── lectura/            # Reference document storage
├── config.json         # Main configuration
└── requirements.txt    # Project dependencies
```

---

## 🤝 Contributing

We follow a strict **issue-first** workflow. Please open an issue to discuss proposed changes before submitting a PR.

1. Fork the repo.
2. Create your feature branch (`git checkout -b feature/AmazingFeature`).
3. Commit your changes (`git commit -m 'feat: Add some AmazingFeature'`).
4. Push to the branch (`git push origin feature/AmazingFeature`).
5. Open a Pull Request.

---

## 📜 License

MIT License. See [LICENSE](LICENSE) for details.

---

# Anti — Agente Autónomo con Memoria Persistente (v0.6) 🇪🇸

Agente autónomo diseñado para ejecución local con memoria persistente real. Anti extrae conocimientos (Engrams) y refina sus propias reglas (Skills) a través de un ciclo de evolución continua.

## ⚡ Inicio Rápido

```bash
git clone --recursive https://github.com/Hunther4/Anti.git
cd Anti
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

## 🛠️ Arquitectura Sentinel Core v0.6
- **Brain**: Motor de inferencia multi-proveedor con gestión dinámica de contexto.
- **Memory**: Sistema de doble capa (Engrams Factuales + Skills Conductuales).
- **Tools**: Loop ReAct con estrategia de búsqueda "En Ola" y extracción de citas.
- **Submódulos**: Integra `agent-search` para investigación web profunda.

## 🧠 Sistema de Memoria
- **Engrams**: Conocimiento factual extraído de interacciones exitosas.
- **Skills**: Reglas de comportamiento en formato Markdown (`SKILL.md`).
- **Evolución**: El comando `reflect` dispara un ciclo de Evolución Dual.

---
**Hunther4** — *Autonomous Evolving Systems*

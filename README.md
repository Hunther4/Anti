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

# Anti — Agente de Auditoría de Seguridad y DevOps (v1.5 Cósmico) 🇪🇸

Anti es un agente autónomo de DevOps y Auditoría de Seguridad en constante evolución, diseñado para la ejecución local segura. Cuenta con persistencia unificada en SQLite FTS5, extensibilidad dinámica mediante plugins intercambiables y ventanas de contexto inteligentes adaptadas según el proveedor.

---

## 💡 Arquitectura y Flujo de Ejecución

```mermaid
graph TD
    User([Usuario]) -->|Pregunta / Comando| TUI[TUI: launcher.go]
    TUI -->|Invocación Async| Agent[AntiAgent: agent.py]
    Agent -->|1. Obtener Memoria Latente| Memory[(SQLite Engine: cold_archive.db)]
    Agent -->|2. Gestión de Ventana Deslizante| ContextMgr[ContextManager]
    ContextMgr -->|Local: 10 mensajes | LLM[Local LLM / LM Studio / Ollama]
    ContextMgr -->|Nube: 100 mensajes| CloudLLM[Cloud LLM / Gemini / Claude]
    LLM & CloudLLM -->|3. Bucle de Pensamiento ReAct| PluginMgr[PluginManager]
    PluginMgr -->|Llama a los Plugins| Tools[AST_AUDIT / WEB_READ / DIFF_AUDIT]
    Tools -->|Resultados de las Herramientas| Agent
    Agent -->|4. PRM Scorer (50 tokens max)| LLMJudge[LLM Juez — Verificación de Calidad]
    LLMJudge -->|Puntuación >= 0.7| Agent
    Agent -->|Respuesta Final Destilada| TUI
```

---

## ⚡ Inicio Rápido

```bash
# Clonar el repositorio con submódulos
git clone --recursive https://github.com/Hunther4/Anti.git
cd Anti

# Instalación rápida (crea venv, instala dependencias y agrega el alias 'anti')
chmod +x install.sh
./install.sh
source ~/.bashrc

# Ejecutar el agente desde el menú de control
anti
```

---

## 🔌 Toolkit de Auditoría y Web (Plugins)

### 🛡️ Auditor de Seguridad AST Python (`AST_AUDIT`)
Utiliza el Árbol de Sintaxis Abstracta (`ast`) nativo de Python para realizar análisis estructural profundo de bases de código Python en milisegundos:
- Detecta ejecuciones inseguras (`eval()`, `exec()`, `os.system()`).
- Escaneo de secretos de alta entropía y contraseñas codificadas en el código fuente.
- Supresiones de excepciones vacías (`except: pass`).

### 🌐 Extractor Limpio de Contenido Web (`WEB_READ`) [NUEVO ⚡]
Un raspador web altamente resistente diseñado para extraer datos factuales puros de cualquier sitio web:
- **Eliminador de Contenido Redundante**: Omite anuncios, encabezados, pies de página y scripts usando BeautifulSoup.
- **Conversión a Markdown**: Entrega Markdown estructurado ultra limpio para ahorrar una cantidad masiva de contexto en las instrucciones.
- **Evasión Anti-Bot**: Encabezados aleatorios simulando navegadores reales.

### 🐙 Auditor de PRs y Diffs (`DIFF_AUDIT`)
Diseñado para inspeccionar cambios pendientes y Pull Requests en busca de vulnerabilidades:
- Descarga dinámicamente parches/diffs desde enlaces de PRs de GitHub.
- Escanea líneas recién agregadas (`+`) en busca de secretos, inyecciones de comandos y malas prácticas de seguridad.

---

## 🧠 Contexto Inteligente y Optimización Local

Anti incorpora ingeniería de punta para mantener los modelos locales (como 35B MoE) extremadamente rápidos, mientras desbloquea razonamiento con contexto completo de largo alcance para APIs en la nube:

### 1. Ventana Deslizante por Proveedor (`max_history_len`)
- **Modo Local (LM Studio, Ollama)**: La ventana de historial dinámico se limita a **10 mensajes (5 turnos)**. Mantiene pequeños los tokens de las instrucciones, ahorra VRAM y logra generación local ultrarrápida.
- **Modo Nube (Claude, Gemini, OpenAI)**: Expande el historial automáticamente a **100 mensajes (50 turnos)**, aprovechando ventanas de contexto de 1M+ tokens para resolver tareas complejas de auditoría en múltiples capas.

### 2. Puntuador de Modelo de Recompensa de Proceso (PRM)
- Evalúa la calidad de la respuesta en tiempo real.
- **Optimización de Latencia Cero**: Las instrucciones se restringen para emitir solo la etiqueta de calificación (`Score: 1/0/-1`) con un límite máximo estricto de **50 tokens**, eliminando por completo la sobrecarga de razonamiento durante la evaluación.
- Se puede activar o desactivar mediante `"enable_prm_scorer"` en `config.json` para máxima velocidad de ejecución directa.

---

## 🔌 Matriz de 9 Proveedores de IA Compatibles

Anti cuenta con soporte de configuración nativa para todos los ecosistemas modernos de IA:

| Proveedor | Tipo | Configuración de Clave de API | Modelos Principales |
| :--- | :---: | :---: | :--- |
| **LM Studio** | Local | *Ninguna* | `Qwen 2.5 35B MoE`, `Llama 3 8B` |
| **Ollama** | Local | *Ninguna* | `mistral`, `codellama`, `deepseek-coder` |
| **OpenAI** | Nube | `OpenAI Key` | `gpt-4o`, `gpt-4-turbo` |
| **Gemini (Google)** | Nube | `Gemini Key` | `gemini-1.5-pro`, `gemini-1.5-flash` |
| **Claude (Anthropic)** | Nube | `Anthropic Key` | `claude-3-5-sonnet`, `claude-3-haiku` |
| **DeepSeek** | Nube | `DeepSeek Key` | `deepseek-chat`, `deepseek-coder` |
| **Minimax** | Nube | `Minimax Key` | `abab6.5g-chat` |
| **OpenAI Compatible** | Híbrido | `OpenAI Comp Key` | *Custom / Groq / Together AI* |

---

## 🤝 Referencia de Comandos CLI

| Comando | Descripción |
| :--- | :--- |
| `status` | Matriz de integridad del sistema, demonio Docker y verificación de memoria SQLite |
| `reflect` | Activa un ciclo de Evolución Dual, compactando engramas y actualizando habilidades conductuales |
| `consolidate` | Activa el mantenimiento de memoria en segundo plano (fusión de nodos de entidades y poda de datos envejecidos) |
| `reasoner` | Activa o desactiva la capa de razonamiento de autocrítica dinámica para depuración compleja |

---

**Hunther4** — *Sistemas Autónomos en Evolución*

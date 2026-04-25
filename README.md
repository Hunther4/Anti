# Anti — Autonomous Agent with Persistent Memory

Un agente de IA local y autonome, construible, con memoria que evoluciona.

---

## ⚡ Quick Start / Inicio Rápido

```bash
# Clone / Clonar
git clone https://github.com/tu-user/Anti.git
cd Anti

# Create venv / Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# Install dependencies / Instalar dependencias
pip install requests aiohttp

# Run / Ejecutar
python -m core.agent
```

---

## 🔌 Supported Providers / Proveedores Soportados

Anti automatically detects which provider you have running:

| Provider | Port | API Key | Auto-detect |
|:---------|:-------|:-------|:---------:|
| **LM Studio** | 1234 | ❌ | ✅ |
| **Ollama** | 11434 | ❌ | ✅ |
| **OpenAI** | cloud | ✅ | ❌ |
| **Gemini** | cloud | ✅ | ❌ |

### How auto-detect works / Cómo funciona el auto-detect

The agent tries in order / El agente prueba en orden:
1. **LM Studio** (port 1234) — if running, use it
2. **Ollama** (port 11434) — if LM Studio fails, try this
3. **Fallback** — uses default if none respond

---

## 🔐 API Keys Configuration / Configuración de API Keys

Only needed if using OpenAI or Gemini. LM Studio and Ollama are 100% local.

### Option A: Interactive Script / Opción A: Script interactivo

```bash
chmod +x setup-keys.sh
./setup-keys.sh
```

### Option B: `.env` file / Opción B: Archivo `.env`

```bash
cp .env.example .env
nano .env
```

### Option C: Environment variable / Opción C: Variable de entorno

```bash
# Temporal
export OPENAI_API_KEY=sk-...

# Permanente / Permanent
echo 'export OPENAI_API_KEY=sk-...' >> ~/.bashrc
source ~/.bashrc
```

---

## 🧠 Persistent Memory / Memoria Persistente

Anti remembers information between sessions:

- **Engrams** — Factual knowledge saved
- **Patrones** — Lessons learned
- **Skills** — Evolved behavior rules
- **Logs** — Conversation history

### Memory Commands / Comandos de memoria

```
reflect    — Analyze experiences and generate new rules
memories  — Show memory summary
engra     — List all engrams
compact   — Compress pattern memory
forget    — Erase all memory
```

---

## 🛠️ Commands / Comandos

```
help          — Show all commands
status        — System and connection status
reasoner      — Toggle auto-critique mode
search <q>   — Force web search
benchmark    — Run SENTINEL GAUNTLET
exit         — Exit
```

---

## 🔒 Security / Seguridad

- ✅ `.gitignore` excludes `.env`, keys, and logs
- ✅ API keys only used in environment variables
- ✅ LM Studio/Ollama are 100% local (no internet)
- ✅ `shell=False` in local commands

---

## 📂 Structure / Estructura

```
Anti/
├── core/
│   ├── agent.py           # Main CLI
│   ├── brain.py          # Chat logic
│   ├── memory.py        # Memory management
│   ├── context_manager.py
│   ├── scorer.py       # PRM evaluation
│   ├── evolver.py      # Skill evolution
│   └── providers/     # Multi-provider
│       ├── base.py
│       ├── lmstudio.py
│       ├── ollama.py
│       ├── openai.py
│       └── gemini.py
├── memory/
│   ├── skills/        # 44 skills
│   ├── engrams/      # Persistent knowledge
│   └── logs.jsonl
├── prompts/
├── workspace/
├── config.json
├── setup-keys.sh
├── .env.example
└── README.md
```

---

## ❓ FAQ

**Do I need GPU?**
For LM Studio or Ollama yes, depends on the model. OpenAI/Gemini use cloud.

**How much RAM?**
- 7B models: ~8GB VRAM
- 13B models: ~16GB VRAM
- 70B models: ~40GB VRAM

**Can I use another model?**
Yes, change `model` in config.json or leave as null to use provider default.

---

## 📜 License / Licencia

MIT — Do whatever you want with it.

---

## 🤝 Contribute / Contribuir

1. Fork
2. Create branch (`git checkout -b feature/foo`)
3. Commit (`git commit -m 'feat: something new'`)
4. Push (`git push origin feature/foo`)
5. Pull Request
# Anti — Autonomous Agent with Persistent Memory

An autonomous AI agent with evolving memory that persists between sessions.

---

## ⚡ Quick Start

```bash
git clone https://github.com/your-user/Anti.git
cd Anti
python -m venv venv && source venv/bin/activate
pip install requests aiohttp
python -m core.agent
```

---

## 🔌 Supported Providers

| Provider | Port | API Key | Notes |
|:---------|:-------|:-------|:-------|
| **LM Studio** | 1234 | ❌ | Auto-detected |
| **Ollama** | 11434 | ❌ | Auto-detected |
| **OpenAI** | cloud | ✅ | Set OPENAI_API_KEY |
| **Gemini** | cloud | ✅ | Set GEMINI_API_KEY |

Set `"provider": "auto"` in config.json for automatic detection.

---

## 🔐 API Keys (Optional)

Only for OpenAI/Gemini. LM Studio/Ollama need no keys.

```bash
# Option 1: Interactive script
./setup-keys.sh

# Option 2: Environment variable
export OPENAI_API_KEY=sk-...
```

---

## 🧠 Memory System

Anti remembers between sessions:
- **Engrams** — factual knowledge
- **Patterns** — lessons learned  
- **Skills** — evolved behavior rules
- **Logs** — conversation history

### Commands

```
reflect   — Analyze experiences, generate new skills
memories  — Show memory summary
engra     — List engrams
forget    — Erase all memory
```

---

## 🛠️ Other Commands

```
help       — Show help
status     — Show system status
search    — Force web search
benchmark — Run performance test
exit      — Exit
```

---

## ⚙️ Configuration

```json
{
  "provider": "auto",
  "model": null,
  "max_iterations": 10,
  "auto_reflect_every_n_tasks": 5
}
```

---

## 📂 Structure

```
core/
├── agent.py        # Main CLI
├── brain.py       # Chat logic
├── memory.py      # Memory
└── providers/    # Multi-provider support
memory/
├── skills/       # 44 skills
└── engrams/     # Persistent knowledge
config.json
```

---

## 🔒 Security

- .gitignore excludes .env and keys
- shell=False prevents injection
- Specific exception handling
- No data sent externally (local providers)

---

## ❓ FAQ

**GPU required?**
Only for local providers (LM Studio/Ollama). Cloud providers need internet only.

**How to change model?**
Load different model in LM Studio/Ollama, or set "model" in config.json.

**What if no provider running?**
Start LM Studio/Ollama, or set API key for OpenAI/Gemini.

---

## 📜 License

See LICENSE file for details.
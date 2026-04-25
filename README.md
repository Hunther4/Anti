# Anti — Autonomous Agent with Persistent Memory

Un agente de IA autónomo con memoria persistente.

---

## ⚡ Quick Start / Inicio Rápido

```bash
# Clone / Clonar
git clone https://github.com/Hunther4/Anti.git
cd Anti

# Create venv / Crear entorno virtual
python -m venv venv
source venv/bin/activate

# Install / Instalar dependencias
pip install requests aiohttp

# Run / Ejecutar
python main.py
```

---

## 🔌 Supported Providers / Proveedores Soportados

| Provider | Port | API Key | Auto-detect |
|:---------|:-------|:-------|:----------:|
| **LM Studio** | 1234 | ❌ | ✅ |
| **Ollama** | 11434 | ❌ | ✅ |
| **OpenAI** | cloud | ✅ | ❌ |
| **Gemini** | cloud | ✅ | ❌ |

Set `"provider": "auto"` in config.json for automatic detection.

---

## 🔐 API Keys (Optional / Opcional)

Only for OpenAI/Gemini. LM Studio/Ollama need no keys.

```bash
# Option 1 / Opción 1
./setup-keys.sh

# Option 2 / Opción 2
export OPENAI_API_KEY=sk-...
```

---

## 🧠 Memory / Memoria

Anti remembers between sessions:
- **Engrams** — factual knowledge
- **Patterns** — lessons learned
- **Skills** — evolved rules
- **Logs** — conversation history

### Commands / Comandos

```
reflect    — Analyze experiences / Analizar experiencias
memories  — Show summary / Mostrar resumen
forget    — Erase all / Borrar todo
```

---

## 🛠️ Other Commands / Otros Comandos

```
help       — Show help / Mostrar ayuda
status     — Show status / Mostrar estado
search    — Force search / Forzar búsqueda
exit      — Exit / Salir
```

---

## 📂 Structure / Estructura

```
src/          # Core code / Código principal
memory/       # Persistent memory / Memoria
workspace/    # Work files / Archivos de trabajo
lectura/      # Reference docs / Docs de referencia
extras/       # Non-core / No esencial
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
Only for local providers (LM Studio/Ollama).

**How to change model?**
Set "model" in config.json or load different model in LM Studio/Ollama.

---

## 📜 License

MIT — See LICENSE file.
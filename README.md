# Anti — Autonomous Agent with Persistent Memory
# Anti — Agente Autónomo con Memoria Persistente

---

## ⚡ Quick Start
## ⚡ Inicio Rápido

```bash
git clone https://github.com/Hunther4/Anti.git
cd Anti

python -m venv venv
source venv/bin/activate

pip install requests aiohttp

python main.py
```

---

## 🔌 Supported Providers
## 🔌 Proveedores Soportados

Anti automatically detects which provider you have running:

| Provider | Port | API Key | Auto-detect |
|:---------|:-------|:-------|:----------:|
| LM Studio | 1234 | ❌ | ✅ |
| Ollama | 11434 | ❌ | ✅ |
| OpenAI | cloud | ✅ | ❌ |
| Gemini | cloud | ✅ | ❌ |

Set `"provider": "auto"` in config.json for automatic detection.

Anti detecta automáticamente qué proveedor tenés ejecutando:

| Proveedor | Puerto | API Key | Auto-detect |
|:---------|:-------|:-------|:----------:|
| LM Studio | 1234 | ❌ | ✅ |
| Ollama | 11434 | ❌ | ✅ |
| OpenAI | cloud | ✅ | ❌ |
| Gemini | cloud | ✅ | ❌ |

Poné `"provider": "auto"` en config.json para detección automática.

---

## 🔐 API Keys Configuration
## 🔐 Configuración de API Keys

Only needed if using OpenAI or Gemini. LM Studio/Ollama need no keys.

### Option 1: Interactive script

```bash
chmod +x setup-keys.sh
./setup-keys.sh
```

### Option 2: Environment variable

```bash
export OPENAI_API_KEY=sk-...
```

Solo necesarias para OpenAI o Gemini. LM Studio/Ollama no necesitan keys.

### Opción 1: Script interactivo

```bash
chmod +x setup-keys.sh
./setup-keys.sh
```

### Opción 2: Variable de entorno

```bash
export OPENAI_API_KEY=sk-...
```

---

## 🧠 Memory System
## 🧠 Sistema de Memoria

Anti remembers information between sessions:

- **Engrams** — factual knowledge
- **Patterns** — lessons learned
- **Skills** — evolved behavior rules
- **Logs** — conversation history

### Commands

```
reflect    — Analyze experiences and generate new skills
memories  — Show memory summary
engra     — List all engrams
forget    — Erase all memory
```

Anti recuerda información entre sesiones:

- **Engrams** — conocimiento fáctico
- **Patrones** — lecciones aprendidas
- **Skills** — reglas de comportamiento evolucionadas
- **Logs** — historial de conversaciones

### Comandos

```
reflect    — Analizar experiencias y generar nuevos skills
memories  — Mostrar resumen de memoria
engra     — Listar todos los engrams
forget    — Borrar toda la memoria
```

---

## 🛠️ Commands
## 🛠️ Comandos

```
help       — Show help
status     — Show system status
search    — Force web search
exit      — Exit
```

```
help       — Mostrar ayuda
status     — Mostrar estado del sistema
search    — Forzar búsqueda web
exit      — Salir
```

---

## 📂 Project Structure
## 📂 Estructura del Proyecto

```
src/          # Core code
memory/       # Persistent memory
workspace/    # Work files
lectura/      # Reference docs
extras/       # Non-core files
```

```
src/          # Código principal
memory/       # Memoria persistente
workspace/    # Archivos de trabajo
lectura/      # Docs de referencia
extras/       # Archivos no esenciales
```

---

## 🔒 Security
## 🔒 Seguridad

- .gitignore excludes .env and keys
- shell=False prevents injection
- Specific exception handling
- No data sent externally (local providers)

- .gitignore excluye .env y claves
- shell=False previene inyección
- Manejo de excepciones específicas
- No se envían datos externamente (proveedores locales)

---

## ❓ FAQ
## ❓ Preguntas Frecuentes

**GPU required?**
Only for local providers (LM Studio/Ollama). Cloud providers need internet only.

**How to change model?**
Set "model" in config.json, or load different model in LM Studio/Ollama.

**¿GPU requerida?**
Solo para proveedores locales (LM Studio/Ollama). Los proveedores en la nube solo necesitan internet.

**¿Cómo cambiar modelo?**
Configurá "model" en config.json, o cargá otro modelo en LM Studio/Ollama.

---

## 📜 License

MIT — See LICENSE file for details.
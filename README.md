# Anti — Agente Autónomo con Memoria Persistente

Un agente de IA local y autónomo, construible, con memoria que evoluciona.

---

## ⚡ Quick Start

```bash
# 1. Clonar
git clone https://github.com/tu-user/Anti.git
cd Anti

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 3. Instalar dependencias
pip install requests aiohttp

# 4. Ejecutar
python -m core.agent
```

---

## 🔌 Proveedores Soportados

Anti detecta automáticamente cuál proveedor tenés ejecutar:

| Proveedor | Puerto | API Key | Auto-detectar |
|:---------|:-------|:-------|:---------:|
| **LM Studio** | 1234 | ❌ | ✅ |
| **Ollama** | 11434 | ❌ | ✅ |
| **OpenAI** | cloud | ✅ | ❌ |
| **Gemini** | cloud | ✅ | ❌ |

### Cómo funciona el auto-detect

El agente prueba en orden:
1. **LM Studio** (puerto 1234) — si está corriendo, lo usa
2. **Ollama** (puerto 11434) — si LM Studio no está, prueba este
3. **Fallback** — usa el default si ninguno responde

```python
# En config.json
{
  "provider": "auto"  // "auto", "lmstudio", "ollama", "openai", "gemini"
}
```

---

## 🔐 Configuración de API Keys (Opcional)

Solo necesitás keys si usás OpenAI o Gemini. LM Studio y Ollama son 100% locales.

### Opción A: Script interactivo

```bash
chmod +x setup-keys.sh
./setup-keys.sh
```

Pedirá la key de forma oculta (`read -s`) y la guardará en `~/.bashrc`. **Nunca se sube a GitHub.**

### Opción B: Archivo `.env`

```bash
cp .env.example .env
nano .env
```

El archivo `.env` está en `.gitignore` — no se sube nunca.

### Opción C: Variable de entorno

```bash
# Temporal
export OPENAI_API_KEY=sk-...

# Permanente
echo 'export OPENAI_API_KEY=sk-...' >> ~/.bashrc
source ~/.bashrc
```

---

## 🧠 Memoria Persistente

Anti记忆 информации entre sesiones:

- **Engrams** — Conocimiento factual guardado
- **Patrones** — Lecciones aprendidas
- **Skills** — Reglas de comportamiento evolucionadas
- **Logs** — Historial de conversaciones

### Comandos de memoria

```
reflect    — Analiza experiencias y genera nuevas reglas
memories   — Muestra resumen de memoria
engra     — Lista todos los engrams
compact   — Comprime la memoria de patrones
forget    — Borra toda la memoria
```

---

## 🎛️ Configuración

```json
{
  "agent_name": "Anti",
  "provider": "auto",
  "model": null,
  "lm_studio_url": "http://127.0.0.1:1234/v1",
  "ollama_url": "http://127.0.0.1:11434",
  "max_iterations": 10,
  "auto_reflect_every_n_tasks": 5
}
```

### Parámetros

| Parámetro | Descripción | Default |
|:---------|:-----------|:--------|
| `provider` | "auto", "lmstudio", "ollama", "openai", "gemini" | "auto" |
| `model` | Modelo específico (null = auto) | null |
| `max_iterations` | Máx iteraciones por tarea | 10 |
| `auto_reflect_every_n_tasks` | Auto-reflexión cada N tareas | 5 |

---

## 🛠️ Comandos

```
help          — Muestra todos los comandos
status       — Estado del sistema y conexión
reasoner     — Activa/desactiva modo auto-critica
search <q>   — Fuerza búsqueda web
benchmark    — Ejecuta SENTINEL GAUNTLET
exit         — Salir
```

---

## 📂 Estructura

```
Anti/
├── core/
│   ├── agent.py           # CLI principal
│   ├── brain.py          # Lógica de chat
│   ├── memory.py        # Gestión de memoria
│   ├── context_manager.py
│   ├��─ scorer.py       # PRM evaluation
│   ├── evolver.py      # Evolución de skills
│   └── providers/     # Multi-provider
│       ├── base.py
│       ├── lmstudio.py
│       ├── ollama.py
│       ├── openai.py
│       └── gemini.py
├── memory/
│   ├── skills/        # 44 skills
│   ├── engrams/      # Conocimiento persistsistente
│   └── logs.jsonl
├── prompts/
├── workspace/
├── config.json
├── setup-keys.sh      # Configurador de API keys
├── .env.example    # Template de variables
└── .gitignore
```

---

## 🏗️ Arquitectura

### Flujo de Auto-Detección

```
1. Agent.start()
2. Cargar config.json
3. provider = config.get("provider")  // "auto"
4. IF provider == "auto":
   - TRY LM Studio (http://127.0.0.1:1234/v1/models)
   - IF fail: TRY Ollama (http://127.0.0.1:11434/api/tags)
   - IF fail: usar default (LM Studio)
5. Crear provider instance
6. Listo para chatear
```

### Proveedores

```python
from core.providers import auto_create, create_provider

# Auto-detectar
provider = auto_create()

# Específico
provider = create_provider("ollama", model="llama3")
```

Cada provider implementa la misma interfaz:
- `chat(messages, temperature) -> (content, usage)`
- `list_models() -> [models]`
- `check_connection() -> bool`

---

## 🔒 Seguridad

- ✅ `.gitignore` excluye `.env`, keys, y logs
- ✅ API keys solo se usan en variable de entorno
- ✅ LM Studio/Ollama 100% local (sin internet)
- ✅ `shell=False` en comandos locales
- ✅ Logging de errores con exception específica

---

## 📝 Commits Recientes

```
ec11cbf fix: Arreglar bare excepts, log rotation, y shell injection
b50a4a1 feat: Agregar soporte multi-provider (LM Studio, Ollama, OpenAI, Gemini)
4088af0 docs: Agregar setup de API keys privado
```

---

## 🤝 Contribuir

1. Fork
2. Crear branch (`git checkout -b feature/foo`)
3. Commit (`git commit -m 'feat: algo nuevo'`)
4. Push (`git push origin feature/foo`)
5. Pull Request

---

## 📜 Licencia

MIT — Hacele lo que quieras.

---

## ❓ FAQ

**¿Necesito GPU?**
Para LM Studio u Ollama sí, dependedel modelo. OpenAI/Gemini usan la cloud.

**¿Cuánta RAM?**
- Modelos 7B: ~8GB VRAM
- Modelos 13B: ~16GB VRAM  
- Modelos 70B: ~40GB VRAM

**¿Puedo usar otro modelo?**
Sí, cambiá `model` en config.json o dejá en null para usar el default del proveedor.

**¿Cómo cambio de proveedor?**
En config.json: `"provider": "ollama"` o `"provider": "openai"`.
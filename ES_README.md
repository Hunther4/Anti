# Anti — Agente Autónomo con Memoria Persistente

Un agente de IA autónomo con memoria que evoluciona entre sesiones.

---

## ⚡ Inicio Rápido

```bash
git clone https://github.com/tu-usuario/Anti.git
cd Anti
python -m venv venv && source venv/bin/activate
pip install requests aiohttp
python -m core.agent
```

---

## 🔌 Proveedores Soportados

| Proveedor | Puerto | API Key | Notas |
|:---------|:-------|:-------|:-------|
| **LM Studio** | 1234 | ❌ | Auto-detectado |
| **Ollama** | 11434 | ❌ | Auto-detectado |
| **OpenAI** | cloud | ✅ | Configurar OPENAI_API_KEY |
| **Gemini** | cloud | ✅ | Configurar GEMINI_API_KEY |

Poné `"provider": "auto"` en config.json para detección automática.

---

## 🔐 API Keys (Opcional)

Solo para OpenAI/Gemini. LM Studio/Ollama no necesitan keys.

```bash
# Opción 1: Script interactivo
./setup-keys.sh

# Opción 2: Variable de entorno
export OPENAI_API_KEY=sk-...
```

---

## 🧠 Sistema de Memoria

Anti recuerda entre sesiones:
- **Engrams** — conocimiento fáctico
- **Patrones** — lecciones aprendidas
- **Skills** — reglas de comportamiento evolucionadas
- **Logs** — historial de conversaciones

### Comandos

```
reflect   — Analizar experiencias, generar nuevos skills
memories  — Mostrar resumen de memoria
engra     — Lista de engrams
forget    — Borrar toda la memoria
```

---

## 🛠️ Otros Comandos

```
help       — Mostrar ayuda
status     — Mostrar estado del sistema
search    — Forzar búsqueda web
benchmark — Ejecutar test de rendimiento
exit      — Salir
```

---

## ⚙️ Configuración

```json
{
  "provider": "auto",
  "model": null,
  "max_iterations": 10,
  "auto_reflect_every_n_tasks": 5
}
```

---

## 📂 Estructura

```
core/
├── agent.py        # CLI principal
├── brain.py       # Lógica de chat
├── memory.py     # Memoria
└── providers/    # Soporte multi-proveedor
memory/
├── skills/       # 44 skills
└── engrams/     # Conocimiento persistente
config.json
```

---

## 🔒 Seguridad

- .gitignore excluye .env y keys
- shell=False previene inyección
- Manejo específico de excepciones
- Sin datos enviados externamente (proveedores locales)

---

## ❓ Preguntas Frecuentes

**¿GPU requerida?**
Solo para proveedores locales (LM Studio/Ollama). Proveedores en la nube necesitan solo internet.

**¿Cómo cambiar modelo?**
Cargá otro modelo en LM Studio/Ollama, o configurá "model" en config.json.

**¿Qué si no hay proveedor corriendo?**
Iniciá LM Studio/Ollama, o configurá API key para OpenAI/Gemini.

---

## 📜 Licencia

Ver archivo LICENSE para detalles.
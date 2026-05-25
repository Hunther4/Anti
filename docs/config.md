# Referencia de Configuración — `config.json`

Archivo central de configuración de Anti. Se encuentra en la raíz del proyecto.

---

## Resumen de Opciones

| Clave | Tipo | Default | Descripción |
| :--- | :---: | :--- | :--- |
| `agent_name` | string | `"Anti"` | Nombre del agente |
| `language` | string | `"es"` | Idioma del agente |
| `personality` | string | *(ver abajo)* | Personalidad del agente (system prompt) |
| `provider` | string | `"auto"` | Proveedor de LLM activo |
| `model` | string \| null | `null` | Modelo específico a usar |
| `lm_studio_url` | string | `"http://127.0.0.1:1234/v1"` | URL del servidor LM Studio |
| `ollama_url` | string | `"http://127.0.0.1:11434"` | URL del servidor Ollama |
| `openai_api_key` | string | — | API key de OpenAI |
| `deepseek_api_key` | string | — | API key de DeepSeek |
| `gemini_api_key` | string | — | API key de Google Gemini |
| `anthropic_api_key` | string | — | API key de Anthropic Claude |
| `minimax_api_key` | string | — | API key de MiniMax |
| `openaicompatible_api_key` | string | — | API key para provider compatible con OpenAI |
| `openaicompatible_url` | string | — | URL para provider compatible con OpenAI |
| `max_iterations` | int | `10` | Máximo de iteraciones del loop ReAct |
| `timeout` | int | `300` | Timeout global en segundos |
| `auto_reflect_every_n_tasks` | int | `5` | Cada N tareas, ejecutar reflexión automática |
| `report_format` | string | `"Vane Style"` | Formato de reportes |
| `enable_prm_scorer` | bool | `true` | Activar/desactivar PRM Scorer |
| `max_history_len_local` | int | `10` | Mensajes en historial para modo local |
| `max_history_len_cloud` | int | `100` | Mensajes en historial para modo cloud |

---

## Detalle de cada opción

### `agent_name`

Nombre que el agente usa para identificarse. Se inyecta en el system prompt.

```json
"agent_name": "Anti"
```

---

### `language`

Idioma principal del agente. Actualmente solo `"es"` (español) tiene system prompts dedicados.

```json
"language": "es"
```

---

### `personality`

Descripción extensa de la personalidad del agente. Se inyecta directamente en el system prompt. El agente recibe esta descripción como instrucción principal de comportamiento.

```json
"personality": "Sos Anti, un Analista Supremo..."
```

---

### `provider`

Proveedor de LLM activo. Acepta:

| Valor | Descripción |
| :--- | :--- |
| `"auto"` | Auto-detección: prueba LM Studio → Ollama en orden |
| `"lmstudio"` | LM Studio (OpenAI-compatible local) |
| `"ollama"` | Ollama (local) |
| `"openai"` | OpenAI API |
| `"gemini"` | Google Gemini API |
| `"deepseek"` | DeepSeek API |
| `"anthropic"` | Anthropic Claude API |
| `"minimax"` | MiniMax API |
| `"openaicompatible"` | Cualquier API compatible con OpenAI (Groq, Together AI, etc.) |

```json
"provider": "auto"
```

---

### `model`

Nombre exacto del modelo a usar. Si es `null`, se auto-detecta según el proveedor.

```json
"model": null
```

Ejemplos:
- `"gpt-4o"`
- `"deepseek-chat"`
- `"claude-3-5-sonnet-20241022"`
- `"gemini-2.5-flash"`
- `"qwen2.5-35b-moe"`

---

### `lm_studio_url`

URL base del servidor LM Studio. Debe apuntar al endpoint compatible con OpenAI.

```json
"lm_studio_url": "http://127.0.0.1:1234/v1"
```

---

### `ollama_url`

URL base del servidor Ollama.

```json
"ollama_url": "http://127.0.0.1:11434"
```

---

### API Keys

Cada proveedor cloud tiene su propia key. Se configuran desde la UI (TUI) o editando `config.json` directamente. También se pueden pasar como variables de entorno (`.env`), pero la prioridad es `config.json` > `.env`.

| Clave | Variable de Entorno |
| :--- | :--- |
| `openai_api_key` | `OPENAI_API_KEY` |
| `deepseek_api_key` | `DEEPSEEK_API_KEY` |
| `gemini_api_key` | `GEMINI_API_KEY` |
| `anthropic_api_key` | `ANTHROPIC_API_KEY` |
| `minimax_api_key` | `MINIMAX_API_KEY` |
| `openaicompatible_api_key` | `OPENAI_COMPATIBLE_API_KEY` |

Todas son opcionales. Sin key, el proveedor cloud no funcionará (el agente muestra advertencia al iniciar).

---

### `max_iterations`

Máximo de iteraciones del loop ReAct (herramientas). Si el agente llega a este límite sin dar una respuesta final, forza la entrega.

```json
"max_iterations": 10
```

---

### `timeout`

Timeout global para llamadas al LLM, en segundos.

```json
"timeout": 300
```

---

### `auto_reflect_every_n_tasks`

Cada N tareas completadas, el agente ejecuta un ciclo de reflexión automática (extrae engrams y evoluciona skills).

```json
"auto_reflect_every_n_tasks": 5
```

---

### `report_format`

Formato de los reportes generados. Actualmente soporta `"Vane Style"`.

```json
"report_format": "Vane Style"
```

---

### `enable_prm_scorer`

Activa o desactiva el Process Reward Model Scorer. Cuando está activo, el agente evalúa cada respuesta con un juez LLM y potencialmente la refina si la calidad es baja (< 0.5 score). Desactivarlo da máxima velocidad.

```json
"enable_prm_scorer": true
```

---

### `max_history_len_local`

Cantidad máxima de mensajes en el historial cuando se usa un proveedor local (LM Studio, Ollama). Valor bajo para ahorrar VRAM y mantener velocidad.

```json
"max_history_len_local": 10
```

---

### `max_history_len_cloud`

Cantidad máxima de mensajes en el historial cuando se usa un proveedor cloud. Valor alto para aprovechar ventanas de contexto largas (1M+ tokens).

```json
"max_history_len_cloud": 100
```

---

## Ejemplo Completo

```json
{
  "agent_name": "Anti",
  "language": "es",
  "personality": "Sos Anti, un Analista Supremo...",
  "provider": "auto",
  "lm_studio_url": "http://127.0.0.1:1234/v1",
  "ollama_url": "http://127.0.0.1:11434",
  "model": null,
  "max_iterations": 10,
  "timeout": 300,
  "auto_reflect_every_n_tasks": 5,
  "report_format": "Vane Style",
  "enable_prm_scorer": true,
  "max_history_len_local": 10,
  "max_history_len_cloud": 100
}
```

---

## Notas

- Las API keys se omiten del ejemplo por seguridad. Se agregan automáticamente al configurar desde el TUI.
- `config.json` está en `.gitignore` las API keys no se suben al repositorio, pero el archivo base sí se trackea.
- Si `provider` es `"auto"`, el agente prueba LM Studio primero, y si no encuentra respuesta, cae a Ollama.
- Al cambiar de provider, las API keys de otros proveedores se preservan en el archivo.

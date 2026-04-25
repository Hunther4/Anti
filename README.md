# Anti — Autonomous Agent with Persistent Memory 🇺🇸

⤵ 🇪🇸

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![GitHub Stars](https://img.shields.io/github/stars/Hunther4/Anti?style=flat)](https://github.com/Hunther4/Anti/stargazers)

---

## ⚡ Quick Start

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

Anti automatically detects which provider you have running. No configuration needed for local providers.

| Provider | Port | API Key | Auto-detect |
|:---------|:-------|:-------|:----------:|
| LM Studio | 1234 | No | Yes |
| Ollama | 11434 | No | Yes |
| OpenAI | cloud | Yes | No |
| Gemini | cloud | Yes | No |

Set `"provider": "auto"` in config.json for automatic detection, or specify a provider directly.

### Provider Performance Recommendation

For tool-heavy workflows involving JSON output, function calling, or structured tool execution, we strongly recommend using models from the **Llama 3.3 8B lineage** (such as Dolphin or Abliterated variants) or **Qwen 2.5 Coder**. These models exhibit significantly lower rates of ethical rejections and false positives when tasked with tool invocation, making them ideal for autonomous agent workflows where reliability is critical.

---

## 🛠️ CLI Commands

| Command | Description |
|:--------|:-----------|
| help | Show all available commands |
| status | Display system status, connection info, and integrity matrix |
| reflect | Force a Dual Evolution cycle. Extract new Engrams from recent logs and refine Skills |
| consolidate | Initiate autonomous maintenance. Purge obsolete data and merge redundant Engram and Skill clusters using LLM |
| memories / engra | Reports on long-term memory retention status |
| search <query> | Force a web search |
| benchmark | Run the Sentinel Gauntlet — 5-phase stress test measuring TPS, latency, and model resilience |
| reasoner | Toggle auto-critique mode (improves accuracy at the cost of higher latency) |
| admin move <src> <dst> | Raw workspace file move operation |
| admin delete <path> | Raw workspace file deletion |
| exit | Exit the agent |

### Extended Command Reference

#### reflect — Dual Evolution Cycle
Forces immediate execution of Anti's self-evolution system:
- Extracts new knowledge Engrams from recent conversation logs
- Analyzes success/failure patterns
- Generates refined behavioral Skills
- Updates the internal skill hierarchy

#### consolidate — Autonomous Maintenance
Initiates full system maintenance:
- Identifies and purges obsolete data
- Merges semantically redundant Engram clusters
- Merges duplicate or overlapping Skill definitions
- Optimizes storage using LLM-guided deduplication

#### reasoner — Auto-Critique Mode
Toggles the internal self-critique loop:
- **ON**: Model generates response → Elite Critic analyzes → Refined output delivered
- **OFF**: Direct response delivery
- Trade-off: Higher quality vs. lower latency

#### benchmark — Sentinel Gauntlet
Executes the 5-phase stress test:
1. **Brute Force**: TPS and latency measurement via complex code generation
2. **Sentinel Integrity**: Context management evaluation
3. **Superior Cognition**: Philosophical/technical reasoning evaluation
4. **Agency**: Tool execution success (SEARCH/READ/WRITE)
5. **Persona Check**: Identity fidelity verification

#### admin — Workspace Management
Raw file operations for advanced users:
- `admin move`: Move files within workspace
- `admin delete`: Delete files from workspace
**Warning**: These operations bypass safety checks. Use with caution.

---

## 🧠 Memory System

One of Anti's most powerful features is its persistent memory system that maintains context between sessions.

- **Engrams** — Factual knowledge the agent learns and remembers
- **Patterns** — Lessons learned from past experiences
- **Skills** — Evolved behavior rules generated automatically
- **Logs** — Complete conversation history with success/failure tracking

### Engram System Architecture

Anti's memory architecture is designed around the concept of "Engrams" — persistent memory units that capture:

1. **Factual Engrams**: Concrete knowledge, facts, and configuration data discovered during interactions
2. **Pattern Engrams**: Recurring behavioral patterns and successful strategies that can be reused
3. **Skill Engrams**: Evolved system behaviors generated through the reflect/consolidate cycle
4. **Log Engrams**: Complete interaction histories with success/failure metrics for continuous improvement

Each Engram is stored with metadata including timestamp, context relevance score, and usage frequency, enabling intelligent retrieval and priority-based management.

---

## 🔐 API Keys Configuration

API keys are only required for cloud providers (OpenAI, Gemini). Local providers (LM Studio, Ollama) work without any keys.

### Interactive Setup

```bash
chmod +x setup-keys.sh
./setup-keys.sh
```

### Manual Setup

```bash
export OPENAI_API_KEY=sk-your-key-here
export GEMINI_API_KEY=your-gemini-key
```

---

## 📂 Project Structure

```
Anti/
├── src/                    # Core source code
│   ├── agent.py           # Main CLI entry point
│   ├── brain.py          # Chat logic and LLM communication
│   ├── memory.py         # Memory management
│   ├── tools.py          # Built-in tools
│   ├── evolver.py        # Skill evolution system
│   ├── compactor.py      # Memory compaction
│   ├── consolidator.py   # Autonomous maintenance
│   ├── scorer.py         # Performance scoring
│   ├── benchmark.py     # Sentinel Gauntlet runner
│   ├── providers/       # Multi-provider support
│   │   ├── lmstudio.py
│   │   ├── ollama.py
│   │   ├── openai.py
│   │   └── gemini.py
│   └── ...
├── memory/                 # Persistent memory
│   ├── skills/          # Behavior skills
│   ├── engrams/        # Factual knowledge
│   └── logs            # Conversation history
├── workspace/             # Work files directory
├── docs/                  # Documentation
├── lectura/              # Reference documents
├── prompts/              # System prompts and templates
├── config.json           # Configuration file
├── main.py               # Entry point
└── setup-keys.sh         # API key setup script
```

---

## 🤝 Contributing

Contributions are welcome! Whether you want to add a new provider, improve the memory system, fix bugs, or add documentation — your help is appreciated.

### How to Contribute

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/amazing-feature`
3. **Make** your changes
4. **Test** thoroughly
5. **Commit** with a clear message: `git commit -m 'feat: add amazing feature'`
6. **Push** to your fork: `git push origin feature/amazing-feature`
7. **Open** a Pull Request

Please ensure your code follows the project's coding standards and include tests for new features.

---

## 📋 Code of Conduct

This project is committed to providing a welcoming and inclusive environment for everyone. We expect all participants to follow these guidelines:

- **Be respectful** and inclusive to all community members
- **Accept constructive criticism** with grace and professionalism
- **Focus on what's best** for the community and the project
- **Show empathy** towards other community members
- **Use welcoming and inclusive language**

Harassment, discrimination, and abusive behavior are not tolerated.

---

## 🔒 Security Policy

If you discover a security vulnerability in this project, please report it responsibly.

### Reporting a Vulnerability

1. **Do NOT** open a public GitHub issue
2. **Email** the maintainer directly with details
3. **Provide** clear steps to reproduce the issue
4. **Allow** reasonable time for a response

We will acknowledge your report and work on a fix as quickly as possible.

---

## ❓ Frequently Asked Questions

**Q: Do I need a GPU?**
A: Only if using local providers (LM Studio or Ollama). Cloud providers (OpenAI, Gemini) work on any computer with internet.

**Q: How do I change the model?**
A: Set the "model" parameter in config.json, or simply load a different model in LM Studio/Ollama before starting Anti.

**Q: What if no provider is running?**
A: Anti will show a connection error. Start LM Studio or Ollama, or configure an API key for OpenAI/Gemini.

**Q: Is my data secure?**
A: Yes. Local providers never send data externally. Cloud providers use standard encryption.

**Q: How does the reflect command work?**
A: `reflect` forces a Dual Evolution cycle: it extracts new Engrams from recent logs, analyzes success/failure patterns, and generates refined behavioral Skills. Think of it as the agent's self-improvement loop.

**Q: What is the Sentinel Gauntlet benchmark?**
A: A 5-phase stress test that measures TPS (Tokens Per Second), latency, context management, tool execution success, and persona fidelity. Essential for evaluating which LLM performs best for your use case.

---

## 📜 License

This project is licensed under the MIT License.

See the [LICENSE](LICENSE) file for full details.

---

## 📝 Authorship

**Anti** was created and is maintained by **Hunther4**.

The project was designed and engineered from **Maule, Chile** — with a laser focus on local, high-performance engineering for autonomous agents. Every architectural decision prioritizes local execution, privacy-by-default, and maximum control over the AI reasoning process.

This is not a generic AI wrapper. Anti is purpose-built for engineers who care about:
- **Local execution** — No data leaves your machine
- **Persistent memory** — True context that survives sessions
- **Autonomous evolution** — Self-improvement through the reflect/consolidate cycle
- **Measurable excellence** — Benchmarks, percentages, and hard metrics

Built from the Maule region for the world.

---

## 🙏 Acknowledgments

- [LM Studio](https://lmstudio.ai) — Local LLM execution
- [Ollama](https://ollama.com) — Local LLM execution
- [OpenAI](https://openai.com) — Cloud AI services
- [Google Gemini](https://gemini.google.com) — Cloud AI services

---

# Anti — Agente Autónomo con Memoria Persistente 🇪🇸

---

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

## 🔌 Proveedores Soportados

Anti detecta automáticamente qué proveedor tenés ejecutando. No necesitás configuración para proveedores locales.

| Proveedor | Puerto | API Key | Auto-detect |
|:---------|:-------|:-------|:----------:|
| LM Studio | 1234 | No | Sí |
| Ollama | 11434 | No | Sí |
| OpenAI | cloud | Sí | No |
| Gemini | cloud | Sí | No |

Poné `"provider": "auto"` en config.json para detección automática, o especificá un proveedor directamente.

### Recomendación de Rendimiento por Proveedor

Para flujos de trabajo intensivos en herramientas que involucran salida JSON, llamadas a funciones o ejecución estructurada de herramientas, recomendamos firmemente usar modelos de la **rama Llama 3.3 8B** (como variantes Dolphin o Abliterated) o **Qwen 2.5 Coder**. Estos modelos exhiben tasas significativamente más bajas de rechazos éticos y falsos positivos cuando se les asigna invocación de herramientas, haciéndolos ideales para flujos de trabajo de agentes autónomos donde la confiabilidad es crítica.

---

## 🛠️ Comandos de CLI

| Comando | Descripción |
|:--------|:-----------|
| help | Mostrar todos los comandos disponibles |
| status | Mostrar estado del sistema, información de conexión y matriz de integridad |
| reflect | Forzar un ciclo de Evolución Dual. Extrae nuevos Engrams de los logs recientes y refina las Skills |
| consolidate | Inicia el mantenimiento autónomo. Purga datos obsoletos y fusiona clusters de Engrams y Skills redundantes mediante el LLM |
| memories / engra | Reportes del estado de retención de la memoria a largo plazo |
| search <consulta> | Forzar una búsqueda web |
| benchmark | Ejecutar el Sentinel Gauntlet — test de estrés de 5 fases para medir TPS, latencia y resiliencia del modelo |
| reasoner | Activar/Desactivar el modo de autocrítica (mejora la precisión a costa de mayor latencia) |
| admin move <origen> <destino> | Operación cruda de movimiento de archivos en el workspace |
| admin delete <ruta> | Eliminación cruda de archivos del workspace |
| exit | Salir del agente |

### Referencia Extendida de Comandos

#### reflect — Ciclo de Evolución Dual
Fuerza la ejecución inmediata del sistema de auto-evolución de Anti:
- Extrae nuevos Engrams de conocimiento de los logs de conversación recientes
- Analiza patrones de éxito/fallo
- Genera Skills conductuales refinadas
- Actualiza la jerarquía interna de skills

#### consolidate — Mantenimiento Autónomo
Inicia el mantenimiento completo del sistema:
- Identifica y purga datos obsoletos
- Fusiona clusters de Engrams semánticamente redundantes
- Fusiona definiciones de Skills duplicadas o superpuestas
- Optimiza el almacenamiento usando desduplicación guiada por LLM

#### reasoner — Modo de Autocrítica
Alterna el loop interno de autocrítica:
- **ON**: El modelo genera respuesta → El Crítico de Élite analiza → Respuesta refinada entregada
- **OFF**: Entrega directa de respuesta
- Balance: Mayor calidad vs. menor latencia

#### benchmark — Sentinel Gauntlet
Ejecuta el test de estrés de 5 fases:
1. **Potencia Bruta**: Medición de TPS y latencia vía generación de código compleja
2. **Integridad Sentinel**: Evaluación de gestión de contexto
3. **Cognición Superior**: Evaluación de razonamiento filosófico/técnico
4. **Agencia**: Éxito de ejecución de herramientas (SEARCH/READ/WRITE)
5. **Persona Check**: Verificación de fidelidad de identidad

#### admin — Gestión del Workspace
Operaciones crudas de archivos para usuarios avanzados:
- `admin move`: Mover archivos dentro del workspace
- `admin delete`: Eliminar archivos del workspace
**Advertencia**: Estas operaciones sortean los controles de seguridad. Usar con precaución.

---

## 🧠 Sistema de Memoria

Una de las características más poderosas de Anti es su sistema de memoria persistente que mantiene contexto entre sesiones.

- **Engrams** — Conocimiento factual que el agente aprende y recuerda
- **Patrones** — Lecciones aprendidas de experiencias pasadas
- **Skills** — Reglas de comportamiento evolucionadas automáticamente
- **Logs** — Historial completo de conversaciones con seguimiento de éxito/fallo

### Arquitectura del Sistema de Engrams

La arquitectura de memoria de Anti está diseñada alrededor del concepto de "Engrams" — unidades de memoria persistente que capturan:

1. **Engrams Factual**: Conocimiento concreto, hechos y datos de configuración descubiertos durante las interacciones
2. **Engrams de Patrones**: Patrones conductuales recurrentes y estrategias exitosas que pueden ser reutilizadas
3. **Engrams de Skills**: Comportamientos del sistema evolucionados generados a través del ciclo reflect/consolidate
4. **Engrams de Logs**: Historiales de interacción completos con métricas de éxito/fallo para mejora continua

Cada Engram se almacena con metadatos incluyendo marca de tiempo, puntuación de relevancia de contexto y frecuencia de uso, permitiendo recuperación inteligente y gestión basada en prioridades.

---

## 🔐 Configuración de API Keys

Las API keys solo son necesarias para proveedores en la nube (OpenAI, Gemini). Los proveedores locales (LM Studio, Ollama) funcionan sin ninguna key.

### Configuración Interactiva

```bash
chmod +x setup-keys.sh
./setup-keys.sh
```

### Configuración Manual

```bash
export OPENAI_API_KEY=sk-tu-key-aqui
export GEMINI_API_KEY=tu-key-de-gemini
```

---

## 📂 Estructura del Proyecto

```
Anti/
├── src/                    # Código fuente principal
│   ├── agent.py           # Punto de entrada del CLI
│   ├── brain.py          # Lógica de chat y comunicación LLM
│   ├── memory.py         # Gestión de memoria
│   ├── tools.py          # Herramientas incorporadas
│   ├── evolver.py        # Sistema de evolución de skills
│   ├── compactor.py      # Compactación de memoria
│   ├── consolidator.py # Mantenimiento autónomo
│   ├── scorer.py        # Puntuación de rendimiento
│   ├── benchmark.py     # Ejecutor del Sentinel Gauntlet
│   ├── providers/       # Soporte multi-proveedor
│   │   ├── lmstudio.py
│   │   ├── ollama.py
│   │   ├── openai.py
│   │   └── gemini.py
│   └── ...
├── memory/                 # Memoria persistente
│   ├── skills/          # Skills de comportamiento
│   ├── engrams/        # Conocimiento factual
│   └── logs            # Historial de conversación
├── workspace/             # Directorio de archivos de trabajo
├── docs/                  # Documentación
├── lectura/               # Documentos de referencia
├── prompts/              # Prompts del sistema y plantillas
├── config.json           # Archivo de configuración
├── main.py               # Punto de entrada
└── setup-keys.sh         # Script de configuración de API keys
```

---

## 🤝 Contribuir

¡Las contribuciones son bienvenidas! Ya sea que quieras agregar un nuevo proveedor, mejorar el sistema de memoria, corregir bugs, o agregar documentación — tu ayuda es apreciada.

### Cómo Contribuir

1. **Hacé fork** del repositorio
2. **Creá** una rama de features: `git checkout -b feature/feature-increible`
3. **Hacé** tus cambios
4. **Probá** exhaustivamente
5. **Commiteá** con un mensaje claro: `git commit -m 'feat: agregar feature increible'`
6. **Pusheá** a tu fork: `git push origin feature/feature-increible`
7. **Abrí** un Pull Request

Por favor asegurate de que tu código siga los estándares de codificación del proyecto e incluyas tests para las nuevas funcionalidades.

---

## 📋 Código de Conducta

Este proyecto está comprometido a proporcionar un ambiente acogedor e inclusivo para todos. Esperamos que todos los participantes sigan estas pautas:

- **Seá respetuoso** e inclusivo con todos los miembros de la comunidad
- **Aceptá la crítica constructiva** con gracia y profesionalismo
- **Enfocá en lo que es mejor** para la comunidad y el proyecto
- **Mostrá empatía** hacia otros miembros de la comunidad
- **Usá lenguaje inclusivo y acogedor**

El acoso, la discriminación y el comportamiento abusivo no serán tolerados.

---

## 🔒 Política de Seguridad

Si descubrís una vulnerabilidad de seguridad en este proyecto, por favor reportala responsablemente.

### Reportando una Vulnerabilidad

1. **NO ABRAS** un issue público en GitHub
2. **Enviá un email** al mantenedor directamente con los detalles
3. **Proporcioná** pasos claros para reproducir el problema
4. **Esperá** un tiempo razonable para una respuesta

Reconoceremos tu reporte y trabajaremos en una solución lo más rápido posible.

---

## ❓ Preguntas Frecuentes

**P: ¿Necesito GPU?**
R: Solo si usás proveedores locales (LM Studio u Ollama). Los proveedores en la nube (OpenAI, Gemini) funcionan en cualquier computadora con internet.

**P: ¿Cómo cambio el modelo?**
R: Configurá el parámetro "model" en config.json, o simplemente cargá un modelo diferente en LM Studio/Ollama antes de iniciar Anti.

**P: ¿Qué pasa si no hay ningún proveedor corriendo?**
R: Anti mostrará un error de conexión. Iniciá LM Studio u Ollama, o configurá una API key para OpenAI/Gemini.

**P: ¿Mis datos están seguros?**
R: Sí. Los proveedores locales nunca envían datos externamente. Los proveedores en la nube usan encriptación estándar.

**P: ¿Cómo funciona el comando reflect?**
R: `reflect` fuerza un ciclo de Evolución Dual: extrae nuevos Engrams de los logs recientes, analiza patrones de éxito/fallo y genera Skills conductuales refinadas. Pensalo como el loop de auto-mejora del agente.

**P: ¿Qué es el benchmark Sentinel Gauntlet?**
R: Un test de estrés de 5 fases que mide TPS (Tokens Per Second), latencia, gestión de contexto, éxito de ejecución de herramientas y fidelidad de personalidad. Esencial para evaluar qué LLM funciona mejor para tu caso de uso.

---

## 📜 Licencia

Este proyecto está licenciado bajo la Licencia MIT.

Ver el archivo [LICENSE](LICENSE) para detalles completos.

---

## 📝 Autoría

**Anti** fue creado y es mantenido por **Hunther4**.

El proyecto fue diseñado e ingeniado desde **Maule, Chile** — con un enfoque de láser en la ingeniería local de alto rendimiento para agentes autónomos. Cada decisión arquitectónica prioriza la ejecución local, privacidad-por-defecto y máximo control sobre el proceso de razonamiento de la IA.

Esto no es un wrapper genérico de IA. Anti está construido especialmente para ingenieros que se preocupan por:
- **Ejecución local** — Ningún dato sale de tu máquina
- **Memoria persistente** — Contexto real que sobrevive entre sesiones
- **Evolución autónoma** — Auto-mejora a través del ciclo reflect/consolidate
- **Excelencia medible** — Benchmarks, porcentajes y métricas duras

Construido desde la región del Maule para el mundo.

---

## 🙏 Agradecimientos

- [LM Studio](https://lmstudio.ai) — Ejecución de LLM local
- [Ollama](https://ollama.com) — Ejecución de LLM local
- [OpenAI](https://openai.com) — Servicios de IA en la nube
- [Google Gemini](https://gemini.google.com) — Servicios de IA en la nube

---

**Star ⭐ if you find this project useful!**

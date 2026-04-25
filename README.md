# Anti — Autonomous Agent with Persistent Memory
# Anti — Agente Autónomo con Memoria Persistente

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

Anti automatically detects which provider you have running. No configuration needed for local providers.

| Provider | Port | API Key | Auto-detect |
|:---------|:-------|:-------|:----------:|
| LM Studio | 1234 | ❌ | ✅ |
| Ollama | 11434 | ❌ | ✅ |
| OpenAI | cloud | ✅ | ❌ |
| Gemini | cloud | ✅ | ❌ |

Set `"provider": "auto"` in config.json for automatic detection, or specify a provider directly.

## 🔌 Proveedores Soportados

Anti detecta automáticamente qué proveedor tenés ejecutando. No necesitás configuración para proveedores locales.

| Proveedor | Puerto | API Key | Auto-detect |
|:---------|:-------|:-------|:----------:|
| LM Studio | 1234 | ❌ | ✅ |
| Ollama | 11434 | ❌ | ✅ |
| OpenAI | cloud | ✅ | ❌ |
| Gemini | cloud | ✅ | ❌ |

Poné `"provider": "auto"` en config.json para detección automática, o especificá un proveedor directamente.

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

## 🧠 Memory System

One of Anti's most powerful features is its persistent memory system that maintains context between sessions.

- **Engrams** — Factual knowledge the agent learns and remembers
- **Patterns** — Lessons learned from past experiences
- **Skills** — Evolved behavior rules generated automatically
- **Logs** — Complete conversation history with success/failure tracking

## 🧠 Sistema de Memoria

Una de las características más poderosas de Anti es su sistema de memoria persistente que mantiene contexto entre sesiones.

- **Engrams** — Conocimiento factual que el agente aprende y recuerda
- **Patrones** — Lecciones aprendidas de experiencias pasadas
- **Skills** — Reglas de comportamiento evolucionadas automáticamente
- **Logs** — Historial completo de conversaciones con seguimiento de éxito/fallo

---

## 🛠️ Available Commands

| Command | Description |
|:--------|:-----------|
| help | Show all available commands |
| status | Display system status and connection info |
| reflect | Analyze recent experiences and generate new skills |
| memories | Show memory summary |
| engra | List all stored engrams |
| search \<query\> | Force a web search |
| benchmark | Run performance benchmark |
| exit | Exit the agent |

## 🛠️ Comandos Disponibles

| Comando | Descripción |
|:--------|:-----------|
| help | Mostrar todos los comandos disponibles |
| status | Mostrar estado del sistema e información de conexión |
| reflect | Analizar experiencias recientes y generar nuevos skills |
| memories | Mostrar resumen de memoria |
| engra | Listar todos los engrams almacenados |
| search \<consulta\> | Forzar una búsqueda web |
| benchmark | Ejecutar benchmark de rendimiento |
| exit | Salir del agente |

---

## 📂 Project Structure

```
Anti/
├── src/                    # Core source code
│   ├── agent.py           # Main CLI entry point
│   ├── brain.py          # Chat logic and LLM communication
│   ├── memory.py         # Memory management
│   ├── tools.py          # Built-in tools
│   ├── providers/       # Multi-provider support
│   │   ├── lmstudio.py
│   │   ├── ollama.py
│   │   ├── openai.py
│   │   └── gemini.py
│   └── ...
├── memory/                 # Persistent memory
│   ├── skills/          # Behavior skills
│   └── engrams/        # Factual knowledge
├── workspace/             # Work files directory
├── lectura/               # Reference documents
├── config.json           # Configuration file
├── main.py               # Entry point
└── setup-keys.sh         # API key setup script
```

## 📂 Estructura del Proyecto

```
Anti/
├── src/                    # Código fuente principal
│   ├── agent.py           # Punto de entrada del CLI
│   ├── brain.py          # Lógica de chat y comunicación LLM
│   ├── memory.py         # Gestión de memoria
│   ├── tools.py          # Herramientas incorporadas
│   ├── providers/       # Soporte multi-proveedor
│   │   ├── lmstudio.py
│   │   ├── ollama.py
│   │   ├── openai.py
│   │   └── gemini.py
│   └── ...
├── memory/                 # Memoria persistente
│   ├── skills/          # Skills de comportamiento
│   └── engrams/        # Conocimiento factual
├── workspace/             # Directorio de archivos de trabajo
├── lectura/               # Documentos de referencia
├── config.json           # Archivo de configuración
├── main.py               # Punto de entrada
└── setup-keys.sh         # Script de configuración de API keys
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

## 📋 Code of Conduct

This project is committed to providing a welcoming and inclusive environment for everyone. We expect all participants to follow these guidelines:

- **Be respectful** and inclusive to all community members
- **Accept constructive criticism** with grace and professionalism
- **Focus on what's best** for the community and the project
- **Show empathy** towards other community members
- **Use welcoming and inclusive language**

Harassment, discrimination, and abusive behavior are not tolerated.

## 📋 Código de Conducta

Este proyecto está comprometido a proporcionar un ambiente acogedor e inclusivo para todos. Esperamos que todos los participantes sigan estas pautas:

- **Seá respetuoso** e inclusivo con todos los miembros de la comunidad
- **Aceptá la crítica constructiva** con gracia y profesionalismo
- **Enfocá en lo que es mejor** para la comunidad y el proyecto
- **Mostrá empatía** hacia otros miembros de la comunidad
- **Usá lenguaje inclusivo y acogedor**

El acoso, la discriminación y el comportamiento abusivo no serán tolerados.

---

## 🔒 Security Policy

If you discover a security vulnerability in this project, please report it responsibly.

### Reporting a Vulnerability

1. **Do NOT** open a public GitHub issue
2. **Email** the maintainer directly with details
3. **Provide** clear steps to reproduce the issue
4. **Allow** reasonable time for a response

We will acknowledge your report and work on a fix as quickly as possible.

## 🔒 Política de Seguridad

Si descubrís una vulnerabilidad de seguridad en este proyecto, por favor reportala responsablemente.

### Reportando una Vulnerabilidad

1. **NO ABRAS** un issue público en GitHub
2. **Enviá un email** al mantenedor directamente con los detalles
3. **Proporcioná** pasos claros para reproducir el problema
4. **Esperá** un tiempo razonable para una respuesta

Reconoceremos tu reporte y trabajaremos en una solución lo más rápido posible.

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

## ❓ Preguntas Frecuentes

**P: ¿Necesito GPU?**
R: Solo si usás proveedores locales (LM Studio u Ollama). Los proveedores en la nube (OpenAI, Gemini) funcionan en cualquier computadora con internet.

**P: ¿Cómo cambio el modelo?**
R: Configurá el parámetro "model" en config.json, o simplemente cargá un modelo diferente en LM Studio/Ollama antes de iniciar Anti.

**P: ¿Qué pasa si no hay ningún proveedor corriendo?**
R: Anti mostrará un error de conexión. Iniciá LM Studio u Ollama, o configurá una API key para OpenAI/Gemini.

**P: ¿Mis datos están seguros?**
R: Sí. Los proveedores locales nunca envían datos externamente. Los proveedores en la nube usan encriptación estándar.

---

## 📜 License

This project is licensed under the MIT License.

See the [LICENSE](LICENSE) file for full details.

## 📜 Licencia

Este proyecto está licenciado bajo la Licencia MIT.

Ver el archivo [LICENSE](LICENSE) para detalles completos.

---

## 🙏 Acknowledgments

- [LM Studio](https://lmstudio.ai) — Local LLM execution
- [Ollama](https://ollama.com) — Local LLM execution
- [OpenAI](https://openai.com) — Cloud AI services
- [Google Gemini](https://gemini.google.com) — Cloud AI services

## 🙏 Agradecimientos

- [LM Studio](https://lmstudio.ai) — Ejecución de LLM local
- [Ollama](https://ollama.com) — Ejecución de LLM local
- [OpenAI](https://openai.com) — Servicios de IA en la nube
- [Google Gemini](https://gemini.google.com) — Servicios de IA en la nube

---

**Star ⭐ if you find this project useful!**

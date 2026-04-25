# Anti — Autonomous Agent with Persistent Memory
# Anti — Agente Autónomo con Memoria Persistente

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![GitHub stars](https://img.shields.io/github/stars/Hunther4/Anti?style=flat)](https://github.com/Hunther4/Anti/stargazers)

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

| Provider | Port | API Key | Auto-detect |
|:---------|:-------|:-------|:----------:|
| LM Studio | 1234 | ❌ | ✅ |
| Ollama | 11434 | 🤖 | ✅ |
| OpenAI | cloud | ✅ | ❌ |
| Gemini | cloud | ✅ | ❌ |

Set `"provider": "auto"` in config.json for automatic detection.

---

## 🔐 API Keys
## 🔐 API Keys

Only needed for OpenAI or Gemini. LM Studio/Ollama need no keys.

```bash
chmod +x setup-keys.sh
./setup-keys.sh
```

Or set environment variable: `export OPENAI_API_KEY=sk-...`

---

## 🧠 Memory
## 🧠 Memoria

- **Engrams** — factual knowledge
- **Patterns** — lessons learned
- **Skills** — evolved rules
- **Logs** — conversation history

---

## 🛠️ Commands

```
help       — Show help
status     — Show system status
reflect    — Analyze experiences
search    — Force web search
exit      — Exit
```

---

## 📂 Structure

```
src/          # Core code
memory/       # Persistent memory
workspace/    # Work files
config.json   # Configuration
```

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests if applicable
5. Commit your changes (`git commit -m 'feat: add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

Please make sure to update tests as appropriate.

---

## 🤝 Contribuir

¡Las contribuciones son bienvenidas! Por favor seguí estos pasos:

1. Hacé fork del repositorio
2. Creá una rama de features (`git checkout -b feature/feature-increible`)
3. Hacé tus cambios
4. Ejecutá los tests si corresponde
5. Commiteá tus cambios (`git commit -m 'feat: agregar feature increible'`)
6. Push a la rama (`git push origin feature/feature-increible`)
7. Abrí un Pull Request

Asegurate de actualizar los tests según corresponda.

---

## 📋 Code of Conduct

This project is committed to a welcoming and inclusive environment. Please be respectful:

- Be kind and courteous
- Accept constructive criticism gracefully
- Focus on what is best for the community
- Show empathy towards other community members

---

## 📋 Código de Conducta

Este proyecto está comprometido con un ambiente acogedor e inclusivo. Por favor sé respetuoso:

- Seá amable y cortés
- Aceptá la crítica constructiva con gracia
- Enfocá en lo que es mejor para la comunidad
- Mostrá empatía hacia otros miembros

---

## 🔒 Security

If you discover a security vulnerability, please send an email instead of opening a public issue.

---

## 🔒 Seguridad

Si descubrís una vulnerabilidad de seguridad, por favor enviá un email en lugar de abrir un issue público.

---

## ❓ FAQ

**GPU required?**
Only for local providers. Cloud providers need internet only.

**How to change model?**
Set "model" in config.json or load different model in your LLM runner.

---

## ❓ Preguntas Frecuentes

**¿GPU requerida?**
Solo para proveedores locales. Los proveedores en la nube solo necesitan internet.

**¿Cómo cambiar modelo?**
Configurá "model" en config.json o cargá otro modelo en tu cliente LLM.

---

## 📜 License

MIT — See LICENSE file for details.

---

## 🙏 Acknowledgments

- [LM Studio](https://lmstudio.ai) — Local LLM running
- [Ollama](https://ollama.com) — Local LLM running
- [OpenAI](https://openai.com) — Cloud AI
- [Google Gemini](https://gemini.google.com) — Cloud AI
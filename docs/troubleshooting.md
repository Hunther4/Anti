# Troubleshooting — Problemas Comunes y Soluciones

---

## 1. Problemas de Conexión con el LLM

### "No se pudo conectar con el proveedor seleccionado"

**Causas posibles:**

- El servidor local no está corriendo.
- La URL del servidor es incorrecta.
- Firewall bloqueando el puerto.

**Soluciones:**

```bash
# Verificar si LM Studio está corriendo
curl http://127.0.0.1:1234/v1/models

# Verificar si Ollama está corriendo
curl http://127.0.0.1:11434/api/tags

# Verificar que config.json tenga las URLs correctas
cat config.json | grep -E "lm_studio_url|ollama_url"
```

Si los curls funcionan pero Anti no conecta, revisá que `config.json` tenga `"provider": "lmstudio"` o `"provider": "ollama"` explícitamente.

### "Error en inferencia: Connection refused"

El servidor LLM local está caído o no acepta conexiones.

**Soluciones:**
1. LM Studio: Abrí LM Studio, cargá un modelo, iniciá el servidor local.
2. Ollama: `ollama serve` o verificá que el servicio esté activo: `systemctl status ollama`.
3. Esperá a que el modelo termine de cargar (puede tomar varios minutos).

---

## 2. Errores de API Key

### "OPENAI_API_KEY no configurada"

El provider cloud está seleccionado pero no hay API key.

**Soluciones:**

1. Configurar desde el TUI: Elegí "Conexiones API" → seleccioná el proveedor → ingresá la key.
2. Configurar manualmente en `config.json`:
   ```json
   "openai_api_key": "sk-tu-key-real-aqui"
   ```
3. Configurar vía `.env`:
   ```bash
   cp .env.example .env
   # Editar .env con las keys reales
   ```

**Verificar que la key funciona:**

```bash
curl -H "Authorization: Bearer sk-tu-key" https://api.openai.com/v1/models
```

### Las API keys no se guardan

El archivo `config.json` debe ser editable. Verificá permisos:

```bash
ls -la config.json
# Si es root-only:
sudo chown $USER:$USER config.json
```

---

## 3. Errores de Docker

### "Docker no está disponible"

El sandbox de ejecución de comandos requiere Docker.

**Soluciones:**

```bash
# Verificar que Docker está instalado
docker --version

# Verificar que el daemon está corriendo
sudo systemctl status docker

# Si no está instalado:
sudo apt install docker.io
sudo usermod -aG docker $USER
# Cerrar sesión y volver a entrar
```

### "docker: permission denied"

El usuario no está en el grupo `docker`.

```bash
sudo usermod -aG docker $USER
# Cerrar sesión y volver a entrar
```

### "Unable to find image 'python:3.12-slim' locally"

Anti necesita descargar la imagen Python para el sandbox. La primera ejecución puede tomar tiempo.

```bash
# Forzar la descarga
docker pull python:3.12-slim
```

### Comando ejecutándose lento en sandbox

El sandbox tiene límites de 512MB de RAM y 1 CPU. Para tareas pesadas, puede ser lento.

---

## 4. Errores de Búsqueda Web

### "SearxNG falló, usando fallback"

SearxNG no está corriendo. Anti usa DuckDuckGo como fallback automático.

**Solución (opcional):**

```bash
cd extras/searxng
docker compose up -d
# SearxNG disponible en http://localhost:8080
```

### Búsquedas devuelven resultados vacíos

- DuckDuckGo puede bloquear scrapers agresivos. Esperá unos minutos y reintentá.
- Google también puede bloquear. Probá con consultas más específicas.
- Revisá que no haya bloqueo de red: `ping google.com`

---

## 5. Errores de Plugins

### "La herramienta X no existe"

El LLM intentó usar una herramienta que no está registrada.

**Verificar plugins cargados:**

```
Anti@Local > plugins
```

**Causas:**
- El plugin tiene un error de sintaxis.
- El plugin no está en `src/plugins/`.
- El nombre del decorador no coincide con lo que el LLM intenta usar.

**Solución:** Revisá los logs del agente para errores de importación.

### Plugin no se carga

```bash
# Verificar que el archivo existe
ls src/plugins/

# Probar la importación manualmente
source venv/bin/activate
python -c "from src.plugins.mi_plugin import *"

# Verificar errores de sintaxis
python -m py_compile src/plugins/mi_plugin.py
```

---

## 6. Problemas de Memoria/Base de Datos

### "Error en FTS5: syntax error"

Sucede cuando la consulta contiene caracteres especiales que FTS5 interpreta como operadores.

**Solución:** El sistema sanitiza automáticamente, pero si ves este error, probá con consultas más simples (sin paréntesis, comillas, etc.).

### Base de datos corrupta

La base de datos SQLite usa modo WAL, que es resistente a corrupción. Si algo sale mal:

```bash
# Respaldar y recrear
cp memory/cold_archive.db memory/cold_archive.db.bak
rm memory/cold_archive.db
# El agente recrea la BD automáticamente al iniciar
```

### "No se encontraron engrams"

La memoria está vacía o la consulta no coincide. Es normal en las primeras ejecuciones. Los engrams se acumulan con el uso.

---

## 7. Problemas del TUI (Go)

### "go: command not found"

El binario `anti` no está compilado o Go no está instalado.

**Soluciones:**
1. Usar el launcher Python: `python3 launcher.py`
2. Compilar el TUI: `go build -o anti launcher.go`

### El TUI Go muestra caracteres raros

El TUI usa caracteres Unicode (emojis, flechas). Si la terminal no los soporta:

- Usá una terminal moderna (GNOME Terminal, kitty, alacritty, Windows Terminal).
- Verificá que `LANG` esté configurado: `export LANG=es_AR.UTF-8`

---

## 8. Errores de Instalación

### "pip install falla"

```bash
# Asegurate de tener Python 3.10+
python3 --version

# Usar virtual env
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Si playwright falla:
playwright install firefox
```

### "install.sh: Permission denied"

```bash
chmod +x install.sh
./install.sh
```

---

## 9. Rendimiento

### Respuestas lentas en modo local

- Modelos grandes (30B+ parámetros) requieren GPUs con suficiente VRAM.
- Reducí `max_history_len_local` en `config.json` a 5 o 6.
- Desactivá `enable_prm_scorer` para saltar la evaluación de calidad.
- Usá modelos más chicos (7B-8B) para respuestas rápidas.

### Respuestas lentas en modo cloud

- El timeout default es 300 segundos. Reducilo si querés fallos más rápidos.
- Algunas APIs (Gemini, Claude) son naturalmente más lentas que otras.
- Verificá tu conexión a internet.

---

## 10. Logs y Depuración

### Ver logs en tiempo real

```bash
tail -f logs/server.log
```

### Nivel de logging

El agente usa `logging` de Python. Para ver más detalles:

```bash
# Antes de ejecutar el agente:
export LOGLEVEL=DEBUG
python main.py
```

### Información de diagnóstico

Usá el comando `status` dentro del agente para ver:

- Estado de conexión con el proveedor
- Cantidad de skills activas
- Cantidad de experiencias registradas
- Estado del Context Manager (carga, eficiencia)
- Archivos en workspace
- Engrams almacenados

---

## 11. Otros

### Ctrl+C no funciona en el agente

El manejador de `KeyboardInterrupt` está implementado en `agent.py`. Si no responde:

```bash
# Matar el proceso manualmente
pkill -f main.py
```

### El agente habla en otro idioma

Verificá `"language": "es"` en `config.json`. También revisá la personalidad, que incluye el idioma del agente.

### Las respuestas son muy largas/cortas

Ajustá el PRM Scorer o la personalidad en `config.json`. La personalidad tiene alta influencia en el estilo de respuesta.

---

## Reportar un Bug

Si encontraste un problema no listado acá:

1. Revisá los logs: `cat logs/server.log | tail -50`
2. Incluí la versión: `git log --oneline -1`
3. Incluí el provider, modelo y configuración usada
4. Abrí un issue en GitHub con los pasos para reproducir

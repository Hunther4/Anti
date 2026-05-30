# 🔍 INFORME 22: Auditoría Arquitectónica y Análisis de Seguridad Integral

## 1. Arquitectura Global (`agent.py`)
**Opinión:** Monolítico y acoplado.

El archivo principal concentra responsabilidades excesivas: instanciación, configuración, loop CLI, renderizado UI y la lógica ReAct del core de inferencia. Esto rompe el Principio de Responsabilidad Única (SRP).

**Mejoras sugeridas:**
- Implementar **Inyección de Dependencias** estricta para desacoplar componentes (memoria, plugins, cerebro).
- Transicionar hacia una **Arquitectura Hexagonal**, aislando la lógica de negocio pura de adaptadores como el CLI o el servidor web.
- Usar un patrón de **Bus de Eventos (Pub/Sub)**, para que tareas paralelas como telemetría, logs y consolidación de memoria actúen de forma asíncrona y reactiva.

---

## 2. Ejecución de Herramientas (`core_tools.py` y `tools.py`)
**Opinión:** Frágil e inseguro (parcialmente mitigado).

Previo a las últimas modificaciones, la herramienta `RUN` validaba únicamente el comando base (`cmd.split()[0]`), abriendo la puerta a inyecciones completas (RCE) si el binario permitido soportaba banderas destructivas. 

**Mejoras sugeridas (más allá del Docker básico):**
- Aislamiento hiper-estricto vía **gVisor o Firecracker**, proporcionando microVMs donde la vulneración del sandbox es drásticamente más difícil.
- Validar el comando no con strings, sino con un **Parser AST de Shell** nativo para identificar todos los subprocesos y pipes maliciosos antes de la ejecución.
- Utilizar **Redes de contenedores efímeras (Air-gapped)** para aislar la ejecución y cerrarlas instantáneamente tras devolver stdout, impidiendo exfiltración.

---

## 3. Motor de Memoria (`memory.py`)
**Opinión:** Primitivo y básico.

La búsqueda semántica depende de un algoritmo TF-IDF manual. Aunque ligero, no comprende el contexto semántico puro de los textos (ej. "manzana" vs "fruta"), limitando severamente el RAG (Retrieval-Augmented Generation).

**Mejoras sugeridas:**
- Migración total hacia una **Vector DB dedicada** (ej. ChromaDB o Qdrant local).
- Integración de **Embeddings neuronales** (modelos de la familia `BGE` o `Nomic-Embed`), para entender el significado del texto y no solo frecuencias de palabras.
- Estrategias de **Chunking semántico**, donde los archivos se dividen por contexto y relaciones sintácticas en vez de simples saltos de línea.

---

## 4. Servidor y API Local (`server.py`) — Falla de Seguridad y Autenticación
**Opinión:** Síncrono y desprotegido.

### La Base del Problema
El servidor actual usa `ThreadingHTTPServer` junto a un simple `SimpleHTTPRequestHandler`.
Si observamos los manejadores `do_GET` (línea 100) y `do_POST` (línea 285) en `server.py`:
```python
    def do_GET(self):
        path_base = self.path.split('?')[0]
        # Inmediatamente evalúa rutas, sin barreras...
        if path_base == '/api/refresh': ...
```
**No existe ninguna verificación de identidad.** Aunque el servidor escucha en `127.0.0.1`, cualquier página web que visites en tu navegador podría intentar realizar un ataque *Cross-Site Request Forgery* (CSRF) enviando un payload malicioso mediante `fetch('http://localhost:8080/api/chat', ...)` sin ser rechazada (dependiendo de políticas CORS laxas o fallas del navegador). Además, cualquier otro usuario u proceso corriendo en tu máquina local tiene acceso administrativo total al Agente.

### 3 Opciones Superiores de Autenticación (Nivel Empresarial/Avanzado)
Dejando de lado soluciones mediocres como las *API Keys planas* en cabeceras HTTP o los *Tokens en URL*:

1. **Sockets UNIX (`.sock`) + Permisos de SO Estrictos**
   En lugar de escuchar en un puerto TCP (`127.0.0.1:8080`), el servidor crea un archivo de socket (ej. `/tmp/anti_agent.sock`). Se aplican permisos `600` o `070` a este archivo. 
   - *Por qué es mejor:* La autenticación recae directamente sobre el Kernel de Linux. Solo el usuario dueño (o el grupo) puede escribir en el socket. Es invulnerable a ataques desde navegadores u otros procesos locales sin permisos.

2. **Autenticación mTLS (Mutual TLS)**
   El servidor no solo usa HTTPS local, sino que exige que el cliente envíe un certificado digital válido emitido por el propio Agente al iniciar.
   - *Por qué es mejor:* Es el estándar en arquitecturas Zero Trust. Si alguien no posee físicamente la clave criptográfica generada dinámicamente en esa sesión, el servidor rechaza la conexión en la capa de transporte (TCP/TLS) antes de siquiera llegar al HTTP parser. Es inyectable de manera inquebrantable.

3. **Tokens JWT (JWE) de Rotación Dinámica**
   Al iniciar el CLI, se genera una llave asimétrica en memoria y un token firmado con un ciclo de vida corto (ej. 15 minutos). El cliente UI inyecta este token y el servidor valida su firma criptográfica.
   - *Por qué es mejor:* Incluso si el token se llega a interceptar (difícil en loopback, pero asumiendo lo peor), su rápida caducidad mitiga el impacto. Además, no se guardan contraseñas en disco duro; todo reside en memoria dinámica de la sesión actual del proceso Python.

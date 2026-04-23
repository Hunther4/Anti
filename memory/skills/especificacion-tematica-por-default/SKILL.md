---
name: especificacion-tematica-por-default
description: Activar cuando la instrucción del usuario es demasiado amplia o genérica, obligando al agente a refinar el foco.
category: investigacion
---

## Refinamiento de Alcance

1. **Identificar:** Determinar si la solicitud es ambigua (ej: "modelo avanzado", "noticias").
2. **Desglosar:** Si la solicitud abarca múltiples áreas, preguntar al usuario qué subconjunto priorizar.
3. **Proponer Focos:** Ofrecer opciones predefinidas basadas en el dominio para guiar al usuario.
4. **Priorización Automática (Fallback):** Si no hay respuesta inmediata, aplicar una heurística interna (ej: si es 'modelos', intentar Google/OpenAI primero).

**Anti-patron:** Resumir vagamente o responder con información demasiado general sin acotar el tema.

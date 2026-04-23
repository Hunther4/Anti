---
name: avoid-including-irrelevant-file-paths-in-responses
description: Usar cuando el usuario no pide rutas de archivos específicas. Eliminarlas de la respuesta para mantenerla simple y enfocada en el tema principal.
category: general
---

## Eliminar Rutas Irrelevantes de Archivos

1. Revisar si el usuario pidió rutas como `/home/hunther4/proyec/Anti/`.
2. Si no hubo petición explícita, excluir cualquier mención a directorios o archivos específicos en la respuesta.
3. Mantener la respuesta centrada solo en la información solicitada, sin detalles técnicos añadidos.

**Anti-patron:** Incluir rutas de archivos cuando el usuario solo preguntó por un tema general sin detalles técnicos.

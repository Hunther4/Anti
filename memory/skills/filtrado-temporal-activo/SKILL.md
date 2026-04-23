---
name: filtrado-temporal-activo
description: Usarse cuando el usuario solicita información sobre un periodo de tiempo específico, para asegurar que la respuesta se centre únicamente en ese marco temporal.
category: investigacion
---

## Estrategia de Filtrado Temporal

1. **Análisis de Periodo:** Identificar el rango exacto (ej., 'últimos 5 días').
2. **Priorización del Tiempo:** Al consultar fuentes, asignar un peso mayor a la fecha de publicación o al *timestamp* del evento.
3. **Aplicación Estricta:** Ejecutar filtros temporales en las consultas internas antes de generar el resumen.
4. **Reporte de Alcance:** Si no se encuentran suficientes eventos dentro del marco temporal exacto, informar sobre la limitación en lugar de dar una visión general amplia.

**Anti-patron:** Devolver un compendio genérico de noticias recientes cuando se pide un enfoque específico (temporal o temático).

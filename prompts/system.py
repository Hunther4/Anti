"""
System prompt builder for Anti-Agent.
Uses Anti-specific BASE_PROMPT from local prompts/templates.py.
"""

from datetime import datetime
from prompts.templates import BASE_PROMPT


def build_system_prompt(name: str, personality: str, omni_context: str = ""):
    """Build the complete system prompt from parts."""
    evolution_rules = ""
    if omni_context and "No hay contexto latente" not in omni_context:
        evolution_rules = f"=== MEMORIA LATENTE E INSTRUCCIONES INYECTADAS ===\n{omni_context}\n==================================================\n"

    now = datetime.now()
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
             "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    current_date = f"{now.day} de {meses[now.month - 1]} de {now.year}, {now.strftime('%H:%M')}"

    prompt = BASE_PROMPT.format(
        name=name,
        personality=personality,
        evolution_rules=evolution_rules,
        current_date=current_date
    )

    return prompt


"""
System prompt builder for Anti-Agent.
Assembles the final system prompt from templates and runtime data.
"""

from datetime import datetime
from prompts.templates import BASE_PROMPT


def build_system_prompt(name, personality, omni_context=""):
    """Build the complete system prompt from parts.

    Args:
        name: Agent name from config
        personality: Agent personality from config
        omni_context: The unified latent memory (Skills, Engrams, Local .md files)

    Returns:
        Complete system prompt string
    """
    evolution_rules = ""
    if omni_context and "No hay contexto latente" not in omni_context:
        evolution_rules = f"=== MEMORIA LATENTE E INSTRUCCIONES INYECTADAS ===\n{omni_context}\n==================================================\n"

    # Inject the real current date so the model never hallucinates it
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


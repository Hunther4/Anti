import asyncio
import os
import sys

# Add current dir to path to find src
sys.path.append(os.path.join(os.getcwd(), "Anti"))

from src.agent import AntiAgent

async def run_test():
    agent = AntiAgent()
    
    prompts = [
        {
            "name": "Complicada 1: Arquitectura Hexagonal & Cold Starts",
            "prompt": "Analizá el impacto de usar una arquitectura hexagonal en un sistema de microservicios serverless (Lambda/Cloud Functions). ¿Cómo manejás la latencia de arranque en frío (cold start) sin sacrificar la inversión de dependencias?",
            "reasoner": False
        },
        {
            "name": "Complicada 2: Race Conditions Distribuidos",
            "prompt": "Tengo un race condition intermitente en un sistema de subastas. El error solo ocurre cuando dos usuarios pujan en el mismo milisegundo desde diferentes zonas geográficas. Proponé una estrategia de sincronización distribuida que no bloquee el event loop de Python.",
            "reasoner": False
        },
        {
            "name": "Reasoner 1: Privacidad vs. Análisis de Sentimiento",
            "prompt": "Estamos diseñando un sistema de monitoreo para empleados. El cliente pide 'análisis de sentimiento' en tiempo real. Hacé una auto-crítica profunda sobre la viabilidad técnica vs. la privacidad. ¿Qué patrones de diseño protegen al usuario final?",
            "reasoner": True
        },
        {
            "name": "Reasoner 2: Optimización Extrema en Microcontroladores",
            "prompt": "Optimizá un algoritmo de búsqueda semántica (embeddings 1536d) para un microcontrolador con 256KB de RAM. Evaluá técnicas de cuantización y reducción de dimensionalidad.",
            "reasoner": True
        },
        {
            "name": "Máxima Dificultad: Inteligencia de Enjambre",
            "prompt": "Diseñá un protocolo de comunicación para un enjambre de bots que deben resolver un laberinto dinámico sin nodo central. El protocolo debe ser resiliente a la pérdida del 40% de los nodos y evitar loops de feedback.",
            "reasoner": True
        }
    ]

    print("=== INICIANDO GAUNTLET EXTREMO PARA ANTI ===")
    
    for i, p in enumerate(prompts):
        print(f"\n--- TEST {i+1}: {p['name']} ---")
        agent.reasoner_mode = p['reasoner']
        
        try:
            result = await agent.handle_command(p['prompt'])
            response = result['response'] if isinstance(result, dict) else result
            print(f"\nRespuesta de Anti (RESUMEN):\n{response[:500]}...")
            
            # Check score if metrics are printed or returned
            # Since Anti uses similar logic to Neu, we expect console metrics
            
        except Exception as e:
            print(f"Error en Test {i+1}: {e}")

    print("\n=== GAUNTLET FINALIZADO ===")

if __name__ == "__main__":
    asyncio.run(run_test())

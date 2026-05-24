import asyncio
import os
import sys

# Add current dir to path to find src
sys.path.append(os.path.join(os.getcwd(), "Anti"))

from src.agent import AntiAgent

async def main():
    agent = AntiAgent()
    
    # Topic: Multi-topic Global Research (Politics, World News, AI, Sports)
    query = "Actualidad política en Chile (abril 2026), principales noticias mundiales, hitos recientes en IA y estado de los preparativos para el próximo mundial."
    
    print(f"=== ANTI-AGENT: EJECUCIÓN AUTÓNOMA DE INVESTIGACIÓN ===")
    print(f"Query: {query}")
    
    # We use RESEARCH tool to trigger parallel fetching
    command = f"RESEARCH {query}"
    
    try:
        result = await agent.handle_command(command)
        response = result['response'] if isinstance(result, dict) else result
        
        print("\n=== REPORTE GENERADO POR ANTI ===")
        print(response)
        
    except Exception as e:
        print(f"Error en la ejecución: {e}")

if __name__ == "__main__":
    asyncio.run(main())

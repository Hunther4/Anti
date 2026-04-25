import asyncio
import os
import sys

# Get the directory where Anti/ core is located
# If running from Anti/, then current dir is fine
# If running from scratch/, we need one level up
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir) # This should be .../proyec/Anti
sys.path.append(project_root)

from src.agent import AntiAgent
from src.benchmark import SentinelGauntlet

async def main():
    agent = AntiAgent()
    # Check connection first
    if not await agent.brain.check_connection():
        print("Error: No se pudo conectar con el servidor de modelos.")
        return
        
    print(f"Conexión exitosa. Iniciando benchmark en: {project_root}")
    runner = SentinelGauntlet(agent)
    report_path = await runner.run()
    print(f"\nBenchmark completado: {report_path}")

if __name__ == "__main__":
    asyncio.run(main())

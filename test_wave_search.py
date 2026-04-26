import asyncio
import sys
import os
sys.path.append(os.path.join(os.getcwd(), "Anti"))
from src.tools import autonomous_research

async def main():
    print("Iniciando test de Búsqueda en Ola...")
    res = await autonomous_research("Mistral Large 2 benchmark oficial")
    print("\n--- RESULTADO DE LA MAGIA ---")
    print(res[:2000] + "\n...(truncado para no saturar)...")

if __name__ == "__main__":
    asyncio.run(main())

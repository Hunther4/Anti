import asyncio
import os
import sys

# Ensure Anti root is in path
sys.path.append(os.getcwd())

from src.agent import AntiAgent

async def run_logic_test():
    print("\n=======================================================")
    print(" INICIANDO PRUEBA RÁPIDA DE LÓGICA Y REGLAS CON ANTI ")
    print("=======================================================\n")
    
    agent = AntiAgent()
    
    # Un acertijo clásico con restricciones de formato estrictas
    prompt = (
        "Resuelve este acertijo siguiendo estrictamente estas 3 reglas:\n"
        "1. Tu respuesta debe ser ÚNICAMENTE un objeto JSON válido con las llaves 'razonamiento' y 'respuesta_final'. No escribas ningún texto fuera del JSON.\n"
        "2. El campo 'respuesta_final' debe ser un único número entero.\n"
        "3. NO utilices ninguna herramienta externa ni invoques comandos entre corchetes.\n\n"
        "Acertijo: Si 5 gatos atrapan 5 ratones en 5 minutos, ¿cuántos minutos tardan 100 gatos en atrapar 100 ratones?"
    )
    
    print(f"Instrucción enviada a Anti:\n> \"{prompt}\"\n")
    print("[*] Enviando petición a LM Studio...")
    
    try:
        result = await agent.handle_command(prompt)
        response = result['response'] if isinstance(result, dict) else result
        
        print("\n================== RESPUESTA DE ANTI ==================")
        print(response)
        print("=======================================================\n")
    except Exception as e:
        print(f"[ERROR] Ocurrió un fallo en el test: {e}")

if __name__ == "__main__":
    asyncio.run(run_logic_test())

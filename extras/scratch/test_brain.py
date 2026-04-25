import asyncio
import os
import sys

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.append(project_root)

from core.brain import Brain

async def test():
    brain = Brain(base_url="http://127.0.0.1:1234/v1")
    print(f"Type of check_connection: {type(brain.check_connection)}")
    import inspect
    print(f"Is coroutine function: {inspect.iscoroutinefunction(brain.check_connection)}")
    res = await brain.check_connection()
    print(f"Result: {res}")

if __name__ == "__main__":
    asyncio.run(test())

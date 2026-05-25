
import asyncio
import sys
from src.tools import run_local_command, fetch_url_text, browser_fetch

async def test_run_local_command():
    print("Testing run_local_command...")
    # This command should be blocked if Docker is not available
    # We use a simple command that would have passed previous blacklist checks
    # (e.g., 'whoami' or 'ls /tmp')
    result = run_local_command("whoami")
    if "SEGURIDAD" in result and "deshabilitada" in result:
        print("✅ run_local_command correctly blocked local execution.")
    elif "docker" in result.lower() or " la salida" in result:
        # If Docker is actually running and working, this is also acceptable, 
        # but we want to prove the fallback is gone.
        # In this environment, if Docker is not available, it MUST return the security message.
        print(f"ℹ️ run_local_command result: {result}")
    else:
        print(f"❌ run_local_command failed security check. Result: {result}")

async def test_fetch_url_text():
    print("\nTesting fetch_url_text...")
    
    test_cases = [
        ("https://www.google.com", True),
        ("http://127.0.0.1", False),
        ("http://localhost", False),
        ("http://192.168.1.1", False),
        ("http://10.0.0.1", False),
        ("http://172.16.0.1", False),
        ("http://169.254.169.254", False),
    ]
    
    for url, should_pass in test_cases:
        result = fetch_url_text(url)
        if should_pass:
            if "SEGURIDAD" not in result:
                print(f"✅ {url} passed (expected)")
            else:
                print(f"❌ {url} blocked (expected pass). Result: {result}")
        else:
            if "SEGURIDAD" in result and "bloqueado" in result:
                print(f"✅ {url} blocked (expected)")
            else:
                print(f"❌ {url} passed (expected block). Result: {result}")

async def test_browser_fetch():
    print("\nTesting browser_fetch...")
    
    test_cases = [
        ("https://www.google.com", True),
        ("http://127.0.0.1", False),
        ("http://localhost", False),
        ("http://192.168.1.1", False),
        ("http://169.254.169.254", False),
    ]
    
    for url, should_pass in test_cases:
        result = await browser_fetch(url)
        if should_pass:
            if "SEGURIDAD" not in result:
                print(f"✅ {url} passed (expected)")
            else:
                print(f"❌ {url} blocked (expected pass). Result: {result}")
        else:
            if "SEGURIDAD" in result and "bloqueado" in result:
                print(f"✅ {url} blocked (expected)")
            else:
                print(f"❌ {url} passed (expected block). Result: {result}")

async def main():
    await test_run_local_command()
    await test_fetch_url_text()
    await test_browser_fetch()

if __name__ == "__main__":
    asyncio.run(main())

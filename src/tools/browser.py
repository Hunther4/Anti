import requests
import re
import html2text
from src.logger import AppLogger
from src.exceptions import ToolError
from src.tools.network import is_safe_url, _is_safe_url_async

app_logger = AppLogger(__name__)

try:
    from playwright.async_api import async_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

async def browser_fetch(url: str) -> str:
    """
    Fetches a URL using a real browser (Firefox) via Playwright.
    Handles JavaScript rendering.
    """
    if not await _is_safe_url_async(url):
        return f"[SEGURIDAD] Acceso bloqueado a la URL: {url}. Las direcciones privadas, loopback o de metadatos de nube están prohibidas."

    if not HAS_PLAYWRIGHT:
        return "[!] Error: Playwright no instalado. Usando fetch_url_text básico.\n" + fetch_url_text(url)

    try:
        async with async_playwright() as p:
            browser = await p.firefox.launch(headless=True)
            page = await browser.new_page(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0"
            )
            
            # Wait for content
            await page.goto(url, wait_until="networkidle", timeout=30000)
            
            # Get text content
            content = await page.evaluate("() => document.body.innerText")
            
            await browser.close()
            return content[:8000]
    except Exception as e:
        app_logger.exception(f"Browser fetch failed for {url}")
        return f"Error en Browser Fetch (Playwright): {e}. Fallback:\n" + fetch_url_text(url)

def fetch_url_text(url: str) -> str:
    """
    Fetch the text content of a URL and clean it up using html2text (Level 2).
    """
    if not is_safe_url(url):
        return f"[SEGURIDAD] Acceso bloqueado a la URL: {url}. Las direcciones privadas, loopback o de metadatos de nube están prohibidas."

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        html = response.text

        h = html2text.HTML2Text()
        h.ignore_links = True
        h.ignore_images = True
        h.ignore_tables = False
        text = h.handle(html)
        
        # Clean up whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text[:8000]
    except Exception as e:
        app_logger.exception(f"URL fetch failed for {url}")
        return f"Error al leer la URL: {e}"

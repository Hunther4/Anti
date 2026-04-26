import asyncio
import os
import requests
import re
import subprocess
import logging
import urllib.parse
from urllib.parse import unquote, quote_plus
from typing import List, Dict, Optional
import sqlite3
import time
import html2text
import json
import itertools

# Optional dependencies
try:
    from playwright.async_api import async_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

logger = logging.getLogger(__name__)

# --- Wigolo Cache & Rerank System (Level 1 & 2) ---
class WigoloCache:
    def __init__(self, db_path="workspace/wigolo_cache.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS search_cache (
                            query TEXT PRIMARY KEY,
                            results TEXT,
                            timestamp REAL
                        )''')

    def get(self, query, max_age_hours=24):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT results, timestamp FROM search_cache WHERE query=?", (query,))
            row = c.fetchone()
            if row and (time.time() - row[1]) < (max_age_hours * 3600):
                return json.loads(row[0])
            return None

    def set(self, query, results):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT OR REPLACE INTO search_cache (query, results, timestamp) VALUES (?, ?, ?)",
                         (query, json.dumps(results), time.time()))

wigolo_cache = WigoloCache()


def run_local_command(command: str) -> str:
    """
    Executes a shell command in the local environment.
    SECURITY: Validates input to prevent shell injection.
    """
    # Security: Block dangerous operators
    dangerous = [';', '&&', '||', '|', '`', '$(', '$(']
    if any(op in command for op in dangerous):
        return f"[SEGURIDAD] Comando bloqueado: contiene operadores peligrosos."
    
    try:
        # Use shell=False to prevent injection
        result = subprocess.run(command.split(), shell=False, capture_output=True, text=True, timeout=30)
        output = result.stdout
        if result.stderr:
            output += f"\n[ERRORES]\n{result.stderr}"
        return output if output.strip() else "Comando ejecutado sin salida (o error silencioso)."
    except Exception as e:
        return f"Error al ejecutar comando: {e}"


def duckduckgo_search(query: str, max_results: int = 5, time_period: str = None) -> str:
    """
    Perform a search using SearxNG local API (JSON).
    Falls back to DuckDuckGo JSON API if SearxNG is offline.
    """
    # Check Wigolo Cache
    cached = wigolo_cache.get(query)
    if cached:
        logger.info(f"Wigolo Cache Hit: {query}")
        return cached

    # 1. Try SearxNG API first (longer timeout for better reliability)
    searxng_url = "http://localhost:8080/search"
    try:
        resp = requests.get(
            searxng_url,
            params={
                "q": query,
                "format": "json",
                "language": "es",
                "categories": "general,news"
            },
            timeout=8
        )
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", [])
            if results:
                output = [f"Resultados (SearxNG) para: '{query}'\n"]
                for i, res in enumerate(results[:max_results]):
                    title = res.get("title", "Sin titulo")
                    url = res.get("url", "")
                    content = res.get("content", "")
                    engine = res.get("engine", "")
                    entry = f"[Fuente {i+1}] {title}\n   URL: {url}"
                    if content:
                        content = re.sub(r'<[^>]+>', '', content).strip()
                        entry += f"\n   Resumen: {content}"
                    if engine:
                        entry += f"\n   Fuente Original: {engine}"
                    output.append(entry)
                final_output = "\n\n".join(output)
                wigolo_cache.set(query, final_output)
                return final_output
    except Exception as e:
        logger.debug(f"SearxNG failed: {e}")
        pass  # Fallback to Google/DuckDuckGo

    # 1.5 Try Google Search Scraper (Robust)
    try:
        google_results = google_search(query, max_results=max_results, time_period=time_period)
        if "No se encontraron resultados" not in google_results:
            wigolo_cache.set(query, google_results)
            return google_results
    except Exception as e:
        logger.debug(f"Google Search failed: {e}")
        pass

    # 2. Fallback: DuckDuckGo Lite API (more reliable than HTML scraping)
    try:
        ddg_url = "https://api.duckduckgo.com/"
        resp = requests.get(
            ddg_url,
            params={"q": query, "format": "json", "no_redirect": 1, "kl": "es-es"},
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            related = data.get("RelatedTopics", [])
            abstract = data.get("AbstractText", "")
            abstract_url = data.get("AbstractURL", "")

            output = [f"Resultados (DuckDuckGo) para: '{query}'\n"]
            if abstract:
                output.append(f"RESUMEN DIRECTO: {abstract}\n   URL: {abstract_url}")
            for i, item in enumerate(related[:max_results]):
                text = item.get("Text", "")
                link = item.get("FirstURL", "")
                if text and link:
                    output.append(f"{i+1}. {text[:200]}\n   URL: {link}")

            if len(output) > 1:
                final_output = "\n\n".join(output)
                wigolo_cache.set(query, final_output)
                return final_output
    except Exception:
        pass

    # 3. Last resort: DuckDuckGo HTML scraper
    url = "https://html.duckduckgo.com/html/"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
        "Accept-Language": "es-ES,es;q=0.9"
    }
    payload = {"q": query, "kl": "es-es"}
    if time_period:
        # DDG HTML uses df=d, df=w, etc.
        payload["df"] = time_period

    try:
        response = requests.post(url, data=payload, headers=headers, timeout=15)
        response.raise_for_status()
        html = response.text

        links = re.findall(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL)
        snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a', html, re.DOTALL)

        if not links:
            return f"No se encontraron resultados para: {query}"

        output = [f"Resultados (DuckDuckGo HTML) para: '{query}'\n"]
        for i, (raw_link, raw_title) in enumerate(links[:max_results]):
            title = re.sub(r'<[^>]+>', '', raw_title).strip()
            link = raw_link
            if "uddg=" in link:
                match = re.search(r'uddg=([^&]+)', link)
                if match:
                    link = unquote(match.group(1))

            snippet = ""
            if i < len(snippets):
                snippet = re.sub(r'<[^>]+>', '', snippets[i]).strip()

            entry = f"[Fuente {i+1}] {title}\n   URL: {link}"
            if snippet:
                entry += f"\n   Resumen: {snippet}"
            output.append(entry)

        final_output = "\n\n".join(output)
        wigolo_cache.set(query, final_output)
        return final_output

    except Exception as e:
        return f"Error en la busqueda: {e}"


def google_search(query: str, max_results: int = 5, time_period: str = None) -> str:
    """
    Scrapes Google Search results.
    time_period: 'd' (day), 'w' (week), 'm' (month), 'y' (year)
    """
    url = "https://www.google.com/search"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Accept-Language": "es-ES,es;q=0.9"
    }
    
    params = {"q": query, "hl": "es"}
    if time_period:
        # qdr:d (day), qdr:w (week), etc.
        params["tbs"] = f"qdr:{time_period}"

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        html = resp.text
        
        # Improved Regex extraction for Google
        # Try multiple patterns for title and link
        matches = re.findall(r'<a\s+href="([^"]+)"[^>]*>.*?<h3[^>]*>(.*?)</h3>', html, re.DOTALL)
        
        if not matches:
            # Fallback pattern for different Google layouts
            matches = re.findall(r'<div class="vv79be">.*?<a\s+href="([^"]+)"[^>]*>.*?<span[^>]*>(.*?)</span>', html, re.DOTALL)

        snippets = re.findall(r'<div class="VwiC3b[^>]*>(.*?)</div>', html, re.DOTALL)
        if not snippets:
             snippets = re.findall(r'<div class="BNeawe s3v9rd AP7Wnd">.*?<div class="BNeawe s3v9rd AP7Wnd">(.*?)</div>', html, re.DOTALL)

        if not matches:
            # Last ditch effort: search for any link that looks like a search result
            matches = re.findall(r'<a\s+href="/url\?q=([^&]+)&[^"]*"><div[^>]*><div[^>]*>(.*?)</div>', html, re.DOTALL)

        if not matches:
            return f"No se encontraron resultados en Google para: {query}"

        output = [f"Resultados (Google) para: '{query}'" + (f" [Tiempo: {time_period}]" if time_period else "") + "\n"]
        
        for i, (link, raw_title) in enumerate(matches[:max_results]):
            title = re.sub(r'<[^>]+>', '', raw_title).strip()
            # Clean Google redirect URLs
            if "/url?q=" in link:
                link = link.split("/url?q=")[1].split("&")[0]
            link = unquote(link)
            
            snippet = ""
            if i < len(snippets):
                snippet = re.sub(r'<[^>]+>', '', snippets[i]).strip()
            
            entry = f"[Fuente {i+1}] {title}\n   URL: {link}"
            if snippet:
                entry += f"\n   Resumen: {snippet}"
            output.append(entry)

        final_output = "\n\n".join(output)
        wigolo_cache.set(query, final_output)
        return final_output
    except Exception as e:
        return f"Error en Google Search: {e}"


async def browser_fetch(url: str) -> str:
    """
    Fetches a URL using a real browser (Firefox) via Playwright.
    Handles JavaScript rendering.
    """
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
        return f"Error en Browser Fetch (Playwright): {e}. Fallback:\n" + fetch_url_text(url)


def fetch_url_text(url: str) -> str:
    """
    Fetch the text content of a URL and clean it up using html2text (Level 2).
    """
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
        return f"Error al leer la URL: {e}"
def write_file(filename: str, content: str, workspace_path: str = "workspace") -> str:
    """
    Write a file to the workspace directory.
    Validates content to prevent placeholders.
    """
    if not is_valid_content(content):
        return "[ERROR] Contenido inválido: se detectaron placeholders o texto insuficiente. Escribí el contenido real y completo."

    if not os.path.exists(workspace_path):
        os.makedirs(workspace_path)
    
    # Security: prevent writing outside workspace
    safe_name = os.path.basename(filename)
    filepath = os.path.join(workspace_path, safe_name)
    
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Archivo '{safe_name}' creado exitosamente en el workspace."
    except Exception as e:
        return f"Error al escribir archivo: {e}"


def read_file(filename: str, workspace_path: str = "workspace") -> str:
    """
    Read a file from the workspace directory.
    """
    safe_name = os.path.basename(filename)
    filepath = os.path.join(workspace_path, safe_name)
    
    if not os.path.exists(filepath):
        return f"Error: El archivo '{safe_name}' no existe."
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error al leer archivo: {e}"


async def autonomous_research(query: str, max_links: int = 5) -> str:
    """
    Level 3: Advanced Wave & Parallel Search Strategy.
    """
    print(f"--- Iniciando investigacion en OLA (Wave Strategy): {query} ---")
    
    # Generate wave queries (Context -> Specific -> Verification)
    queries = [
        query,
        f"{query} contexto general explicacion",
        f"{query} benchmark oficial documentacion"
    ]
    
    search_results_raw = ""
    all_urls = []
    
    # Execute searches sequentially to populate results but gather URLs
    for q in queries:
        res = await asyncio.to_thread(duckduckgo_search, q, max_results=3)
        search_results_raw += f"\n\n--- Resultados Ola: '{q}' ---\n" + res
        urls = re.findall(r'URL: (https?://[^\s\n]+)', res)
        all_urls.extend(urls)

    if not all_urls:
        # Mandatory citations fallback
        print("Fallback Citas Obligatorias: No se hallaron URLs, intentando Google Scraper directo...")
        res = await asyncio.to_thread(google_search, query, max_results=max_links)
        urls = re.findall(r'URL: (https?://[^\s\n]+)', res)
        all_urls.extend(urls)
        search_results_raw += "\n\n--- Resultados Fallback ---\n" + res

    # Dedup URLs preserving order
    unique_urls = list(dict.fromkeys(all_urls))[:max_links]

    consolidated = [
        f"INFORME DE INVESTIGACION: {query}\n",
        "--- RESUMEN DE BUSQUEDA EN OLA ---\n",
        search_results_raw[:4000] + "\n...(truncado)...\n",
        "\n--- ANALISIS DE FUENTES (DESTILADO WIGOLO) ---\n"
    ]

    async def _fetch_and_format(i, url):
        print(f"--- Extrayendo y destilando (Link {i+1}): {url} ---")
        if HAS_PLAYWRIGHT:
            content = await browser_fetch(url)
        else:
            content = await asyncio.to_thread(fetch_url_text, url)
        
        # Simple distillation: take key sentences or segments
        snippet = content[:3000]
        # Remove common noise patterns
        snippet = re.sub(r'\s+', ' ', snippet).strip()
        
        return f"\n[FUENTE {i+1}] {url}\nEXTRACTO CLAVE: {snippet}..."

    # Launch all fetches in parallel
    tasks = [_fetch_and_format(i, url) for i, url in enumerate(unique_urls)]
    source_reports = await asyncio.gather(*tasks)
    
    consolidated.extend(source_reports)
    consolidated.append("\n--- FIN DE INVESTIGACION ---\n")
    consolidated.append("INSTRUCCION: Usa estos datos para generar tu informe final. No uses placeholders.")
    
    return "\n".join(consolidated)

def is_valid_content(content: str) -> bool:
    """
    Validación robusta v2 - balance entre estricto y funcional
    """
    if not content or len(content.strip()) < 20:
        return False
    
    content_lower = content.lower()
    obvious_placeholders = [
        '...', '......', '.........',
        'contenido...', 'contenido extenso',
        'aquí va', 'aqui va', 'placeholder',
        'texto generado', 'resumen en proceso',
        'respuesta:', 'contenido:',
    ]
    
    for p in obvious_placeholders:
        if p in content_lower:
            return False
            
    bad_patterns = [
        r'^\.{3,}$',
        r'^\s*\.{3,}\s*$',
        r'^\[contenido\]$',
        r'^contenido\s+extenso\.?$',
    ]
    
    for pattern in bad_patterns:
        if re.search(pattern, content_lower, re.MULTILINE):
            return False
            
    lines = [l.strip() for l in content.split('\n') if l.strip()]
    sentences = re.split(r'[.!?]+', content)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    if len(lines) < 3 and len(sentences) < 3:
        words = re.findall(r'\b[a-zA-Záéíóúñ]{4,}\b', content)
        if len(words) < 5:
            return False
            
    return True

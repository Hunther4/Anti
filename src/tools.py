import os
import requests
import re
import subprocess
from urllib.parse import unquote


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


def duckduckgo_search(query: str, max_results: int = 5) -> str:
    """
    Perform a search using SearxNG local API (JSON).
    Falls back to DuckDuckGo JSON API if SearxNG is offline.
    """
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
                return "\n\n".join(output)
    except Exception:
        pass  # Fallback to DuckDuckGo

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
                return "\n\n".join(output)
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

        return "\n\n".join(output)

    except Exception as e:
        return f"Error en la busqueda: {e}"


def fetch_url_text(url: str) -> str:
    """
    Fetch the text content of a URL and clean it up.
    Removes scripts, styles, and other non-content tags.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        html = response.text

        # 1. Remove non-content elements
        html = re.sub(r'<(script|style|nav|footer|header|aside)[^>]*>.*?</\1>', '', html, flags=re.DOTALL | re.IGNORECASE)
        
        # 2. Remove comments
        html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)
        
        # 3. Strip all other tags
        text = re.sub(r'<[^>]+>', ' ', html)
        
        # 4. Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # 5. Handle common HTML entities
        text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')

        return text[:7000]  # Even more space for clean text
    except Exception as e:
        return f"Error al leer la URL: {e}"
def write_file(filename: str, content: str, workspace_path: str = "workspace") -> str:
    """
    Write a file to the workspace directory.
    """
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


def autonomous_research(query: str, max_links: int = 5) -> str:
    """
    Performs a search and automatically fetches the content of the top links.
    Returns a consolidated report with distilled digests.
    """
    print(f"--- Iniciando investigacion autonoma: {query} ---")
    search_results_raw = duckduckgo_search(query, max_results=max_links)
    
    if "No se encontraron resultados" in search_results_raw:
        return search_results_raw

    # Extract URLs from search results
    urls = re.findall(r'URL: (https?://[^\s\n]+)', search_results_raw)
    
    consolidated = [
        f"INFORME DE INVESTIGACION: {query}\n",
        "--- RESUMEN DE BUSQUEDA ---\n",
        search_results_raw,
        "\n--- ANALISIS DE FUENTES (DESTILADO) ---\n"
    ]
    
    for i, url in enumerate(urls[:max_links]):
        print(f"--- Extrayendo y destilando (Link {i+1}): {url} ---")
        content = fetch_url_text(url)
        
        # Simple distillation: take key sentences or segments
        # In a real scenario, this could be a small model call, but here we do it procedurally
        snippet = content[:2500]
        # Remove common noise patterns
        snippet = re.sub(r'\s+', ' ', snippet).strip()
        
        consolidated.append(f"\n[FUENTE {i+1}] {url}")
        consolidated.append(f"EXTRACTO CLAVE: {snippet}...")
        
    consolidated.append("\n--- FIN DE INVESTIGACION ---\n")
    consolidated.append("INSTRUCCION: Usa estos datos para generar tu informe final. No uses placeholders.")
    
    return "\n".join(consolidated)

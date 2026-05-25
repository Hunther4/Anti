import re
import requests
from bs4 import BeautifulSoup
import html2text
from src.plugin_manager import anti_tool

def clean_html_content(html: str) -> str:
    """
    Strips headers, footers, sidebars, and nav elements from HTML
    to isolate the main body text, saving massive prompt tokens.
    """
    soup = BeautifulSoup(html, "html.parser")
    
    # Remove clutter elements
    for element in soup(["script", "style", "nav", "header", "footer", "aside", "form"]):
        element.decompose()
        
    # Attempt to locate the main content areas
    main_content = None
    for selector in ["main", "article", "#content", ".content", "#main", ".main"]:
        found = soup.select_one(selector)
        if found:
            main_content = found
            break
            
    content_soup = main_content if main_content else soup
    
    # Convert cleaned HTML to clean Markdown
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = True
    h.ignore_tables = False
    h.body_width = 0  # No word wrap
    
    markdown_text = h.handle(str(content_soup))
    
    # Clean redundant whitespace and empty lines
    markdown_text = re.sub(r'\n{3,}', '\n\n', markdown_text)
    markdown_text = re.sub(r' +', ' ', markdown_text)
    
    return markdown_text.strip()

@anti_tool(name="WEB_READ", description="Lee el contenido de cualquier página web y lo convierte en Markdown limpio sin publicidad, menús o código CSS/JS redundante. Uso: WEB_READ: https://example.com")
def web_read_tool(raw_args: str) -> str:
    url = raw_args.strip()
    if not url:
        return "[ERROR] Por favor especifica una URL válida. Uso: WEB_READ: https://sitio.com"
        
    if not (url.startswith("http://") or url.startswith("https://")):
        # Auto-prepend protocol
        url = "https://" + url

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3"
    }

    try:
        print(f"[*] Conectando a {url} para extraer contenido limpio...")
        response = requests.get(url, headers=headers, timeout=12)
        response.raise_for_status()
        
        # Detect encoding
        if response.encoding is None or response.encoding == 'ISO-8859-1':
            response.encoding = response.apparent_encoding
            
        markdown_content = clean_html_content(response.text)
        
        if not markdown_content:
            return f"[ERROR] No se pudo extraer texto relevante de la página {url}."
            
        # Hard cap to prevent token explosion but keep it rich
        char_cap = 9000
        truncated_suffix = "\n\n... [Contenido truncado para optimizar el prompt del Agente] ..."
        
        if len(markdown_content) > char_cap:
            return markdown_content[:char_cap] + truncated_suffix
            
        return markdown_content

    except requests.exceptions.HTTPError as he:
        return f"[ERROR HTTP] Fallo al leer {url}: {he}"
    except requests.exceptions.Timeout:
        return f"[ERROR] Tiempo de espera agotado al conectar a {url} (límite de 12s)."
    except Exception as e:
        return f"[ERROR General] Ocurrió un error inesperado al leer la página: {e}"

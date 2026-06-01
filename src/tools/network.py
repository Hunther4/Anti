import asyncio
import socket
import ipaddress
import urllib.parse
from src.logger import AppLogger

app_logger = AppLogger(__name__)

def is_safe_url(url: str) -> bool:
    """
    Validates that the URL does not point to private IP ranges, 
    loopback addresses, or cloud metadata endpoints (SSRF protection).
    Prevents DNS rebinding by checking all resolved IP addresses.
    """
    try:
        parsed = urllib.parse.urlparse(url)
        if not parsed.hostname:
            return False
        
        # Resolve all IP addresses for the hostname to prevent DNS rebinding
        # socket.getaddrinfo returns a list of 5-tuples: (family, type, proto, canonname, sockaddr)
        addr_info = socket.getaddrinfo(parsed.hostname, parsed.port or (80 if parsed.scheme == 'http' else 443))
        
        for item in addr_info:
            ip_address_str = item[4][0]
            ip = ipaddress.ip_address(ip_address_str)
            
            if ip.is_loopback:
                return False
            if ip.is_private:
                return False
            if str(ip) == "169.254.169.254":
                return False
                
        return True
    except Exception as e:
        # If we can't resolve or parse, we treat it as unsafe for security
        app_logger.debug(f"URL safety check failed for {url}: {e}")
        return False

async def _is_safe_url_async(url: str) -> bool:
    """Async version of is_safe_url that doesn't block the event loop."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, is_safe_url, url)

import os

def parse_document(filepath: str) -> str:
    """
    Parses various document types into plain text with auto-encoding detection
    and adaptive semantic chunking for large files.
    """
    chunk_index = None
    if "#chunk" in filepath:
        filepath, chunk_part = filepath.split("#chunk", 1)
        try:
            chunk_index = int(chunk_part) - 1
        except ValueError:
            pass

    if not os.path.exists(filepath):
        return f"Error: El archivo '{filepath}' no existe."

    ext = os.path.splitext(filepath)[1].lower()
    
    # 1. Intentar decodificar secuencialmente con encodings comunes
    raw_content = ""
    try:
        if ext in [".txt", ".md", ".py", ".go", ".js", ".json", ".csv", ".yaml", ".yml", ".ts", ".rs", ".sh"]:
            for encoding in ["utf-8", "latin-1", "cp1252"]:
                try:
                    with open(filepath, "r", encoding=encoding, errors="strict") as f:
                        raw_content = f.read()
                        break
                except UnicodeDecodeError:
                    continue
            else:
                # Fallback final si todos los encodings estrictos fallan
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    raw_content = f.read()
        
        elif ext == ".pdf":
            try:
                import pypdf
                reader = pypdf.PdfReader(filepath)
                text = []
                for page in reader.pages:
                    text.append(page.extract_text() or "")
                raw_content = "\n".join(text)
            except ImportError:
                return "Error: Para leer archivos PDF se requiere 'pypdf'. Instala con 'pip install pypdf'."
            except Exception as e:
                return f"Error al leer PDF: {e}"
        
        else:
            return f"Error: El formato '{ext}' no está soportado actualmente."
            
    except Exception as e:
        return f"Error al procesar el documento: {e}"

    # 2. Motor de Chunking Adaptativo y Paginación
    content_len = len(raw_content)
    # Límite adaptativo de 15,000 caracteres
    limit = 15000
    chunk_size = 10000
    overlap = 1500

    if content_len <= limit:
        return raw_content

    # Crear fragmentos (chunks)
    chunks = []
    start = 0
    while start < content_len:
        end = min(start + chunk_size, content_len)
        chunks.append(raw_content[start:end])
        if end >= content_len:
            break
        start += (chunk_size - overlap)

    total_chunks = len(chunks)
    
    if chunk_index is not None:
        if 0 <= chunk_index < total_chunks:
            selected_content = chunks[chunk_index]
            header = (
                f"--- [PAGINACIÓN ANTI] Archivo: '{os.path.basename(filepath)}' "
                f"| Parte {chunk_index + 1} de {total_chunks} ---\n"
            )
            footer = ""
            if chunk_index + 1 < total_chunks:
                footer = f"\n\n--- [NOTA] Hay más partes disponibles. Usá READ con '{os.path.basename(filepath)}#chunk{chunk_index + 2}' para continuar leyendo. ---"
            return header + selected_content + footer
        else:
            return f"[ERROR] El fragmento {chunk_index + 1} solicitado no existe. Total de partes: {total_chunks}."

    # Si no se solicitó un chunk específico, devolver el primer fragmento e instrucciones de navegación
    first_content = chunks[0]
    header = (
        f"--- [PAGINACIÓN ANTI] El archivo '{os.path.basename(filepath)}' es extenso ({content_len} caracteres) "
        f"y se fragmentó en {total_chunks} partes de forma adaptativa. ---\n"
        f"--- Mostrando Parte 1 de {total_chunks} ---\n\n"
    )
    footer = (
        f"\n\n--- [NOTA] Mostrando solo la primera parte para evitar token-explosion. "
        f"Para leer la siguiente parte, usá READ con '{os.path.basename(filepath)}#chunk2'. Total partes: {total_chunks}. ---"
    )
    return header + first_content + footer

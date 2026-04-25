import os

def parse_document(filepath: str) -> str:
    """
    Parses various document types into plain text.
    Supported: .txt, .md, .py, .js, .json, .csv
    Planned: .pdf, .docx
    """
    if not os.path.exists(filepath):
        return f"Error: El archivo '{filepath}' no existe."

    ext = os.path.splitext(filepath)[1].lower()
    
    try:
        if ext in [".txt", ".md", ".py", ".js", ".json", ".csv", ".yaml", ".yml"]:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        
        elif ext == ".pdf":
            try:
                import pypdf
                reader = pypdf.PdfReader(filepath)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return text
            except ImportError:
                return "Error: Para leer archivos PDF se requiere 'pypdf'. Instala con 'pip install pypdf'."
            except Exception as e:
                return f"Error al leer PDF: {e}"
        
        else:
            return f"Error: El formato '{ext}' no esta soportado actualmente."
            
    except Exception as e:
        return f"Error al procesar el documento: {e}"

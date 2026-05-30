import sys
import os
sys.path.append(os.path.join(os.getcwd(), "Anti"))
from src.tools import google_search

def main():
    print("Testeando Google Scraper directo...")
    res = google_search("clima en santiago de chile hoy")
    print("\n--- RESULTADO ---")
    print(res)

if __name__ == "__main__":
    main()

import sqlite3
import os

db_path = "/home/hunther4/proyec/Anti/memory/cold_archive.db"

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check for missing columns and add them
    try:
        cursor.execute("ALTER TABLE engram_archive ADD COLUMN score REAL DEFAULT 1.0")
        print("Column 'score' added.")
    except sqlite3.OperationalError:
        print("Column 'score' already exists or error.")
        
    try:
        cursor.execute("ALTER TABLE engram_archive ADD COLUMN last_accessed_at TIMESTAMP")
        print("Column 'last_accessed_at' added.")
    except sqlite3.OperationalError:
        print("Column 'last_accessed_at' already exists or error.")
        
    conn.commit()
    conn.close()
    print("Database patch applied.")
else:
    print("Database file not found. It will be created correctly on next run.")

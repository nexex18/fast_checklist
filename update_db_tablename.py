import sqlite3
import json
from pathlib import Path
import shutil
from datetime import datetime

def migrate_database():
    DB_PATH = Path('data/checklists.db')
    BACKUP_PATH = Path('data/checklists_backup.db')
    
    # Create backup
    if DB_PATH.exists():
        shutil.copy(DB_PATH, BACKUP_PATH)
        print(f"Created backup at {BACKUP_PATH}")
    
    # Read existing data
    old_data = {'checklists': [], 'steps': []}
    if BACKUP_PATH.exists():
        with sqlite3.connect(BACKUP_PATH) as conn:
            cur = conn.cursor()
            
            # Check what tables exist
            cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cur.fetchall()]
            print(f"Found tables: {tables}")
            
            # Get checklists
            if 'checklists' in tables:
                cur.execute("SELECT id, title, description, created_at FROM checklists")
                for row in cur.fetchall():
                    old_data['checklists'].append({
                        'id': row[0],
                        'title': row[1],
                        'description': row[2],
                        'description_long': '',  # New field
                        'created_at': row[3]
                    })
                print(f"Found {len(old_data['checklists'])} checklists")
            
            # Get steps
            if 'steps' in tables:
                cur.execute("SELECT id, checklist_id, text, status FROM steps")
                for row in cur.fetchall():
                    old_data['steps'].append({
                        'id': row[0],
                        'checklist_id': row[1],
                        'text': row[2],
                        'status': row[3],
                        'order_index': 0,  # New field
                        'reference_material': json.dumps([])  # New field
                    })
                print(f"Found {len(old_data['steps'])} steps")
    
    # Delete existing database
    if DB_PATH.exists():
        DB_PATH.unlink()
        for ext in ['-wal', '-shm']:
            path = DB_PATH.parent / f"{DB_PATH.name}{ext}"
            if path.exists(): 
                path.unlink()
    
    # Create new database with updated schema
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        
        # Create new tables
        cur.execute("""
        CREATE TABLE checklists (
            id INTEGER PRIMARY KEY,
            title TEXT,
            description TEXT,
            description_long TEXT,
            created_at TEXT
        )
        """)
        
        cur.execute("""
        CREATE TABLE steps (
            id INTEGER PRIMARY KEY,
            checklist_id INTEGER,
            text TEXT,
            status TEXT,
            order_index INTEGER,
            reference_material TEXT
        )
        """)
        
        # Restore data
        if old_data['checklists']:
            cur.executemany(
                "INSERT INTO checklists (id, title, description, description_long, created_at) VALUES (?, ?, ?, ?, ?)",
                [(c['id'], c['title'], c['description'], c['description_long'], c['created_at']) 
                 for c in old_data['checklists']]
            )
        
        if old_data['steps']:
            cur.executemany(
                "INSERT INTO steps (id, checklist_id, text, status, order_index, reference_material) VALUES (?, ?, ?, ?, ?, ?)",
                [(s['id'], s['checklist_id'], s['text'], s['status'], s['order_index'], s['reference_material']) 
                 for s in old_data['steps']]
            )
    
    print("Migration completed successfully!")
    return len(old_data['checklists']), len(old_data['steps'])

# Run migration
if __name__ == "__main__":
    checklists, steps = migrate_database()
    print(f"Migrated {checklists} checklists and {steps} steps")

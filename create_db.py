import sqlite3
from datetime import datetime
from pathlib import Path

# Ensure data directory exists
Path('data').mkdir(exist_ok=True)

# Create fresh database
db_path = 'data/checklists.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Create tables
cursor.execute('''
CREATE TABLE IF NOT EXISTS checklists (
    id INTEGER PRIMARY KEY,
    title TEXT,
    description TEXT,
    created_at TEXT
)''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY,
    checklist_id INTEGER,
    text TEXT,
    status TEXT,
    FOREIGN KEY (checklist_id) REFERENCES checklists (id)
)''')

# Sample data
sample_checklists = [
    ('Daily Standup Tasks', 'Items to cover in daily standup', datetime.now().isoformat()),
    ('Project Launch Checklist', 'Steps needed before going live', datetime.now().isoformat()),
    ('Weekly Review Items', 'Topics for weekly team review', datetime.now().isoformat()),
    ('Development Setup', 'New developer environment setup steps', datetime.now().isoformat()),
    ('Code Review Guidelines', 'Standard items to check in code reviews', datetime.now().isoformat())
]

# Insert sample data
cursor.executemany('INSERT INTO checklists (title, description, created_at) VALUES (?, ?, ?)', 
                  sample_checklists)

conn.commit()
conn.close()

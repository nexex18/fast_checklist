#db_connection

import sqlite3
from pathlib import Path

DB_PATH = Path('data/checklists.db')

class DBConnection:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        
    def __enter__(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        return self.conn.cursor()
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.commit()
        self.conn.close()

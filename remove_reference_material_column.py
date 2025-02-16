from db_connection import DBConnection

def remove_reference_material_column():
    with DBConnection() as cursor:
        # First check if the column exists
        cursor.execute("""
            SELECT COUNT(*) 
            FROM pragma_table_info('steps') 
            WHERE name='reference_material'
        """)
        if cursor.fetchone()[0] > 0:
            print("Removing reference_material column...")
            # SQLite doesn't support DROP COLUMN directly, so we need to:
            # 1. Create new table without the column
            # 2. Copy data
            # 3. Drop old table
            # 4. Rename new table
            cursor.executescript("""
                CREATE TABLE steps_new (
                    id INTEGER PRIMARY KEY,
                    checklist_id INTEGER,
                    text TEXT,
                    status TEXT,
                    order_index INTEGER
                );
                
                INSERT INTO steps_new (id, checklist_id, text, status, order_index)
                SELECT id, checklist_id, text, status, order_index
                FROM steps;
                
                DROP TABLE steps;
                
                ALTER TABLE steps_new RENAME TO steps;
            """)
            print("Column removed successfully")
        else:
            print("Column reference_material does not exist")

with DBConnection() as cursor:
    cursor.execute("PRAGMA table_info('steps')")
    print("\nSteps table columns:")
    for col in cursor.fetchall():
        print(dict(col))

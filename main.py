import os
from fasthtml.common import *
from fasthtml.common import RedirectResponse as redirect
from monsterui.all import *
from pathlib import Path
from datetime import datetime
import argparse
import sys
import sqlite3

# Add this near the top of your file, after imports
parser = argparse.ArgumentParser()
parser.add_argument('-refresh', action='store_true', help='Refresh the database on startup')
args = parser.parse_args()

# Then modify your database initialization code
DB_PATH = Path('data/checklists.db')

# Make sure the data directory exists
os.makedirs('data', exist_ok=True)

# Only delete and recreate if -refresh flag is used
if args.refresh and DB_PATH.exists():
    print("Refreshing database...")
    DB_PATH.unlink()
    # Remove WAL files if they exist
    wal = DB_PATH.parent / f"{DB_PATH.name}-wal"
    shm = DB_PATH.parent / f"{DB_PATH.name}-shm"
    if wal.exists(): wal.unlink()
    if shm.exists(): shm.unlink()


# Setup tables configuration with explicit id column
table_config = {
    'checklists': {
        'id': int,
        'title': str,
        'description': str,
        'created_at': str,
        'pk': 'id'
    },
    'items': {
        'id': int,
        'checklist_id': int,
        'text': str,
        'status': str,
        'pk': 'id'
    }
}

# Create FastHTML app with SQLite database and unpack all returned values
app, rt, checklists, items = fast_app(
    str(DB_PATH),  # First positional argument
    checklists=table_config['checklists'],
    items=table_config['items'],
    hdrs=Theme.blue.headers()  # keyword arguments at the end
)


# def format_date(date_str):
#     dt = datetime.fromisoformat(date_str)
#     return dt.strftime('%Y-%m-%d %H:%M')

def checklist_table():
    conn = sqlite3.connect('data/checklists.db')
    cursor = conn.cursor()
    cursor.execute("SELECT title, description FROM checklists")
    data = [{'Title': row[0], 'Description': row[1]} 
            for row in cursor.fetchall()]
    conn.close()
    
    header_data = ['Title', 'Description']
    
    def body_render(k, v):
        match k:
            case 'Title': return Td(v, cls='font-bold')
            case _: return Td(v)
    
    return TableFromDicts(header_data, data, 
        header_cell_render=lambda v: Th(v.upper()),
        body_cell_render=body_render)

def create_checklist_modal():
    return Modal(
        ModalTitle("Create New Checklist"),
        ModalBody(
            Form(
                LabelInput("Title", id="title", placeholder="Checklist Title"),
                LabelTextArea("Description", id="description", placeholder="Description"),
                action="/create",
                method="POST",
                id="new-checklist-form"  # Add form ID for reference
            )
        ),
        footer=DivRAligned(
            ModalCloseButton("Cancel", cls=ButtonT.default),  # Fixed cancel button
            Button("Create", cls=ButtonT.primary, type="submit", form="new-checklist-form")  # Link button to form
        ),
        id='new-checklist-modal'
    )

def render_checklist_page(table):
    return ft('div',
        ft('div', 
            ft('div', 
                ft('div',
                    ft('button', "New Checklist", cls='uk-button uk-button-primary', 
                       **{'uk-toggle': 'target: #new-checklist-modal'}),
                    cls='uk-width-1-1'),
                ft('div',
                    ft('h2', "Checklists", cls='uk-heading-small'),
                    cls='uk-width-1-1 uk-margin-small-top'),
                ft('div', table, cls='uk-width-1-1'),
                cls='uk-grid uk-grid-small'
            ),
            cls='uk-container'
        ),
        create_checklist_modal()
    )

@rt('/')
async def get(req):
    lists = checklists[0]()
    table = checklist_table()
    return render_checklist_page(table)


@rt('/create')
async def post(req):
    form = await req.form()
    checklist = {
        'title': form['title'],
        'description': form.get('description', ''),
        'created_at': datetime.now().isoformat()
    }
    checklists[0].insert(checklist)
    return RedirectResponse('/', status_code=303)  # 303 See Other forces a GET request


if __name__ == '__main__':
    serve()

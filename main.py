import os
from fasthtml.common import *
from fasthtml.common import RedirectResponse as redirect
from monsterui.all import *
from pathlib import Path
from datetime import datetime
import argparse

# CLI Arguments
parser = argparse.ArgumentParser()
parser.add_argument('-refresh', action='store_true', help='Refresh the database on startup')
args = parser.parse_args()

# Database Setup
DB_PATH = Path('data/checklists.db')
os.makedirs('data', exist_ok=True)

if args.refresh and DB_PATH.exists():
    print("Refreshing database...")
    DB_PATH.unlink()
    for ext in ['-wal', '-shm']:
        path = DB_PATH.parent / f"{DB_PATH.name}{ext}"
        if path.exists(): path.unlink()

# Table Configuration
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

# FastHTML App Setup
app, rt, checklists, items = fast_app(
    str(DB_PATH),
    checklists=table_config['checklists'],
    items=table_config['items'],
    hdrs=Theme.blue.headers()
)

# UI Components
def checklist_table():
    data = [{'Title': row.title, 'Description': row.description} 
            for row in checklists[0]()]
    
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
                id="new-checklist-form"
            )
        ),
        footer=DivRAligned(
            ModalCloseButton("Cancel", cls=ButtonT.default),
            Button("Create", cls=ButtonT.primary, type="submit", form="new-checklist-form")
        ),
        id='new-checklist-modal'
    )

def render_checklist_page(table):
    return Container(
        Div(
            Button("New Checklist", cls=ButtonT.primary, **{'uk-toggle': 'target: #new-checklist-modal'}),
            H2("Checklists", cls='uk-heading-small uk-margin-top'),
            table,
            cls='uk-margin'
        ),
        create_checklist_modal()
    )

# Routes
@rt('/')
async def get(req):
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
    return RedirectResponse('/', status_code=303)

if __name__ == '__main__':
    serve()

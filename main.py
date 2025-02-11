import os
from fasthtml.common import *
from fasthtml.common import RedirectResponse as redirect
from monsterui.all import *
from pathlib import Path
from datetime import datetime
import argparse
import json  # For handling reference_material JSON

import sqlite3


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

# Updated table configuration
table_config = {
    'checklists': {
        'id': int,
        'title': str,
        'description': str,
        'description_long': str,
        'created_at': str,
        'pk': 'id'
    },
    'steps': {
        'id': int,
        'checklist_id': int,
        'text': str,
        'status': str,
        'order_index': int,
        'reference_material': str,  # Will store URLs as JSON string
        'pk': 'id'
    }
}


# FastHTML App Setup
app, rt, checklists, steps = fast_app(  # Changed 'items' to 'steps'
    str(DB_PATH),
    checklists=table_config['checklists'],
    steps=table_config['steps'],  # Changed from 'items' to 'steps'
    hdrs=Theme.blue.headers()
)

def checklist_row(checklist):
    return Tr(
        Td(
            Div(
                Span(checklist.title, cls='font-bold mr-2'),
                Span(f"({checklist.created_at[:10]})", cls='uk-text-muted uk-text-small'),
                cls='uk-flex uk-flex-middle'
            )
        ),
        Td(
            Div(
                A("View", 
                  cls='uk-link-text uk-margin-small-right',
                  **{
                      'hx-get': f'/checklist/{checklist.id}',
                      'hx-target': '#main-content',
                      'hx-push-url': 'true'
                  }),
                A("Edit", cls='uk-link-text uk-margin-small-right'),
                A("Delete", cls='uk-link-text uk-text-danger'),
                cls='uk-flex uk-flex-middle uk-flex-right'
            )
        )
    )

# UI Components
def checklist_table():
    conn = sqlite3.connect('data/checklists.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, description, description_long, created_at FROM checklists")
    rows = cursor.fetchall()
    conn.close()
    
    data = [SimpleNamespace(
        id=row[0],
        title=row[1],
        description=row[2],
        description_long=row[3],
        created_at=row[4]
    ) for row in rows]
    
    return Table(
        Thead(
            Tr(
                Th("Checklist"),
                Th("Actions", cls='uk-text-right')
            )
        ),
        Tbody(*(checklist_row(checklist) for checklist in data)),
        cls="uk-table uk-table-divider uk-table-hover uk-table-small"
    )

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

def render_checklist_page(checklist_id):
    # Get the data
    checklist = get_checklist(checklist_id)
    steps = get_checklist_steps(checklist_id)
    
    # Combine into a single view
    return Div(
        # Header with back button
        Div(
            A("← Back", cls="uk-link-text", **{'hx-get': '/', 'hx-target': '#main-content'}),
            cls="uk-margin-bottom"
        ),
        # Checklist details
        H2(checklist.title, cls="uk-heading-small"),
        P(checklist.description, cls="uk-text-meta"),
        P(checklist.description_long) if checklist.description_long else "",
        
        # Steps section
        render_steps(steps),
        
        cls="uk-margin",
        id="main-content"
    )

def get_checklist(checklist_id):
    conn = sqlite3.connect('data/checklists.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, title, description, description_long, created_at 
        FROM checklists WHERE id = ?
    """, (checklist_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return SimpleNamespace(
            id=row[0],
            title=row[1],
            description=row[2],
            description_long=row[3],
            created_at=row[4]
        )
    return None

def get_checklist_steps(checklist_id):
    conn = sqlite3.connect('data/checklists.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, text, status, order_index, reference_material
        FROM steps 
        WHERE checklist_id = ?
        ORDER BY order_index
    """, (checklist_id,))
    rows = cursor.fetchall()
    conn.close()
    
    return [SimpleNamespace(
        id=row[0],
        text=row[1],
        status=row[2],
        order_index=row[3],
        reference_material=row[4]
    ) for row in rows]

def render_steps(steps):
    return Div(
        H3("Steps", cls="uk-heading-small uk-margin-top"),
        Ul(*(
            Li(
                Div(
                    P(
                        Span(step.text, cls="uk-text-emphasis"),
                        Span(f" ({step.status})", cls="uk-text-muted uk-text-small"),
                        cls="uk-margin-small-bottom"
                    ),
                    P(A("Reference", href=step.reference_material.strip('"[]'))) 
                    if step.reference_material and step.reference_material != '[]' 
                    else "",
                    cls="uk-margin-small"
                )
            ) for step in steps
        ), cls="uk-list uk-list-divider")
    )

def render_main_page():
    return Div(
        # Header
        H1("My Checklists", cls="uk-heading-medium"),
        # Add new checklist button
        Button("+ New Checklist", 
               cls="uk-button uk-button-primary uk-margin-bottom",
               **{'uk-toggle': 'target: #new-checklist-modal'}),
        # List of checklists
        checklist_table(),
        # Add the modal
        create_checklist_modal(),
        cls="uk-container uk-margin-top",
        id="main-content"
    )


# Routes
@rt('/')
async def get(req):
    return render_main_page()


@rt('/create')
async def post(req):
    form = await req.form()
    checklist = {
        'title': form['title'],
        'description': form.get('description', ''),
        'description_long': '',  # Added this field
        'created_at': datetime.now().isoformat()
    }
    checklists[0].insert(checklist)
    return RedirectResponse('/', status_code=303)


@rt('/checklist/{checklist_id}')
def get(req):
    checklist_id = int(req.path_params['checklist_id'])
    return render_checklist_page(checklist_id)  # Now passing the parameter


if __name__ == '__main__':
    serve()

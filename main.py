import os
from fasthtml.common import *
from fasthtml.common import RedirectResponse as redirect
from monsterui.all import *
from pathlib import Path
from datetime import datetime
import argparse
import json  # For handling reference_material JSON
from fastcore.basics import AttrDict, patch


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

class DBConnection:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        
    def __enter__(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # This allows column access by name
        return self.conn.cursor()
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.commit()
        self.conn.close()

class Checklist(AttrDict):
    def __init__(self, id, title, description, description_long='', created_at=None, steps=None):
        super().__init__(
            id=id,
            title=title,
            description=description,
            description_long=description_long,
            created_at=created_at,
            steps=steps or []
        )


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
app, rt, checklists, steps = fast_app(  
    str(DB_PATH),
    checklists=table_config['checklists'],
    steps=table_config['steps'],  
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
                A("Delete", 
                  cls='uk-link-text uk-text-danger',
                  **{
                      'hx-delete': f'/checklist/{checklist.id}',
                      'hx-confirm': 'Are you sure you want to delete this checklist?',
                      'hx-target': '#main-content'
                  }),
                cls='uk-flex uk-flex-middle uk-flex-right'
            )
        )
    )


# UI Components

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

def get_checklist_with_steps(checklist_id):
    with DBConnection() as cursor:
        cursor.execute("""
            SELECT id, title, description, description_long, created_at 
            FROM checklists WHERE id = ?
        """, (checklist_id,))
        checklist_row = cursor.fetchone()
        
        if not checklist_row:
            return None
            
        cursor.execute("""
            SELECT id, text, status, order_index, reference_material
            FROM steps 
            WHERE checklist_id = ?
            ORDER BY order_index
        """, (checklist_id,))
        step_rows = cursor.fetchall()
    
    # Create the checklist using our new class
    return Checklist(
        id=checklist_row['id'],
        title=checklist_row['title'],
        description=checklist_row['description'],
        description_long=checklist_row['description_long'],
        created_at=checklist_row['created_at'],
        steps=[AttrDict(
            id=row['id'],
            text=row['text'],
            status=row['status'],
            order_index=row['order_index'],
            reference_material=row['reference_material']
        ) for row in step_rows]
    )
    

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

def render_checklist_page(checklist_id):
    # Get the combined data using our new function
    checklist = get_checklist_with_steps(checklist_id)
    
    if not checklist:
        return Div("Checklist not found", cls="uk-alert uk-alert-danger")
    
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
        
        # Steps section - now using checklist.steps directly
        render_steps(checklist.steps),
        
        cls="uk-margin",
        id="main-content"
    )


def checklist_table():
    with DBConnection() as cursor:
        cursor.execute("""
            SELECT id, title, description, description_long, created_at 
            FROM checklists
        """)
        rows = cursor.fetchall()
    
    data = [Checklist(
        id=row['id'],
        title=row['title'],
        description=row['description'],
        description_long=row['description_long'],
        created_at=row['created_at']
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
    try:
        checklist = Checklist(
            id=None,  # Database will auto-assign ID
            title=form['title'],
            description=form.get('description', ''),
            description_long='',
            created_at=datetime.now().isoformat(),
            steps=[]
        )
        # Convert AttrDict to dict for database insertion
        checklist_data = dict(checklist)
        del checklist_data['steps']  # Remove steps as it's not a database field
        del checklist_data['id']     # Remove id to let database auto-assign
        
        print("Checklist data to insert:", checklist_data)  # Debug print
        result = checklists[0].insert(checklist_data)
        print("Insert result:", result)  # Debug print
        
        return RedirectResponse('/', status_code=303)
    except Exception as e:
        print(f"Error creating checklist: {e}")  # Debug print
        raise



@rt('/checklist/{checklist_id}')
def get(req):
    checklist_id = int(req.path_params['checklist_id'])
    return render_checklist_page(checklist_id)  # Now passing the parameter


from fastcore.basics import patch

@patch
def delete(self:Checklist):
    with DBConnection() as cursor:
        # First delete associated steps
        cursor.execute("""
            DELETE FROM steps 
            WHERE checklist_id = ?
        """, (self.id,))
        
        # Then delete the checklist
        cursor.execute("""
            DELETE FROM checklists 
            WHERE id = ?
        """, (self.id,))
        
        return cursor.rowcount > 0


@rt('/checklist/{checklist_id}')
async def delete(req):
    checklist_id = int(req.path_params['checklist_id'])
    checklist = get_checklist_with_steps(checklist_id)
    if checklist:
        checklist.delete()
    return render_main_page()


if __name__ == '__main__':
    serve()

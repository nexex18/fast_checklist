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

hdrs = Theme.blue.headers() + [
    '<script src="https://unpkg.com/htmx.org/dist/ext/sortable.js"></script>'
]

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
                A("Edit",
                  cls='uk-link-text uk-margin-small-right',
                  **{
                      'hx-get': f'/checklist/{checklist.id}/edit',
                      'hx-target': '#main-content',
                      'hx-push-url': 'true'
                  }),
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
        Script(src="https://unpkg.com/htmx.org/dist/ext/sortable.js"),
        Script(src="https://cdn.jsdelivr.net/npm/sortablejs@1.15.0/Sortable.min.js"),
        # Rest of your existing render_main_page code...
        H1("My Checklists", cls="uk-heading-medium"),
        Button("+ New Checklist", 
               cls="uk-button uk-button-primary uk-margin-bottom",
               **{'uk-toggle': 'target: #new-checklist-modal'}),
        checklist_table(),
        create_checklist_modal(),
        cls="uk-container uk-margin-top",
        id="main-content"
    )

def render_new_step_modal(checklist_id, current_step_count):
    return Modal(
        ModalTitle("Add New Step"),
        ModalBody(
            Form(
                LabelInput(label="Step Text", 
                          id="step_text",
                          placeholder="Enter step description",
                          cls="uk-margin-small"),
                LabelSelect(label="Status",  # Fixed: added 'label=' keyword
                           id="step_status",
                           options=['Not Started', 'In Progress', 'Completed'],
                           value='Not Started',
                           cls="uk-margin-small"),
                LabelInput(label="Reference Link",
                          id="step_ref",
                          placeholder="Optional reference URL",
                          cls="uk-margin-small"),
                LabelInput(label="Position",
                          id="step_position",
                          type="number",
                          value=str(current_step_count + 1),
                          min="1",
                          max=str(current_step_count + 1),
                          cls="uk-margin-small"),
                action=f"/checklist/{checklist_id}/step",
                method="POST",
                id="new-step-form"
            )
        ),
        footer=DivRAligned(
            ModalCloseButton("Cancel", cls=ButtonT.default),
            Button("Add Step", 
                  cls=ButtonT.primary, 
                  type="submit",
                  form="new-step-form")
        ),
        id='new-step-modal'
    )


def render_checklist_edit(checklist):
    return Div(
        Script(src="https://unpkg.com/htmx.org/dist/ext/sortable.js"),
        Script(src="https://cdn.jsdelivr.net/npm/sortablejs@1.15.0/Sortable.min.js"),
        # Header with back button
        Div(
            A("← Back", cls="uk-link-text", **{'hx-get': f'/checklist/{checklist.id}', 'hx-target': '#main-content'}),
            cls="uk-margin-bottom"
        ),
        # Edit form for checklist details
        Form(
            # Title and Add button in same line
            Div(
                H2("Edit Checklist", cls="uk-heading-small uk-margin-remove"),
                A("➕",
                  cls="uk-link-muted uk-button uk-button-small",
                  **{'uk-toggle': 'target: #new-step-modal'}),  # Updated to trigger modal
                cls="uk-flex uk-flex-middle uk-flex-between"
            ),
            
            LabelInput("Title", 
                      id="title", 
                      value=checklist.title,
                      cls="uk-margin-small"),
            LabelTextArea("Description", 
                         id="description",
                         value=checklist.description,
                         cls="uk-margin-small"),
            LabelTextArea("Long Description", 
                         id="description_long",
                         value=checklist.description_long,
                         cls="uk-margin-small"),
            
            # Steps section with sortable
            H3("Steps", cls="uk-heading-small uk-margin-top"),
            Div(*(
                Div(
                    # Add drag handle and make sortable
                    Div(
                        Span("⋮⋮", cls="uk-margin-small-right drag-handle"),
                        Span(f"Step {i+1}", cls="uk-form-label"),
                        A("🗑️",
                          cls="uk-link-danger uk-margin-small-left",
                          **{
                              'hx-delete': f'/checklist/{checklist.id}/step/{step.id}',
                              'hx-confirm': 'Are you sure you want to delete this step?',
                              'hx-target': '#main-content'
                          }),
                        cls="uk-flex uk-flex-middle",
                        style="cursor: move"
                    ),
                    LabelInput(label="", 
                             id=f"step_{step.id}_text",
                             value=step.text),
                    Div(
                        LabelSelect(label="Status",
                                  id=f"step_{step.id}_status",
                                  options=['Not Started', 'In Progress', 'Completed'],
                                  value=step.status,
                                  cls="uk-width-1-2"),
                        LabelInput(label="Reference",
                                 id=f"step_{step.id}_ref",
                                 value=step.reference_material.strip('"[]'),
                                 cls="uk-width-1-2"),
                        cls="uk-grid-small uk-child-width-1-2@s",
                        **{'uk-grid': ''}
                    ),
                    cls="uk-margin-medium-bottom",
                    **{
                        'name': 'steps',
                        'data-id': step.id
                    }
                )
                for i, step in enumerate(checklist.steps)
            ),
            **{
                'id': 'sortable-steps',
                'hx-ext': 'sortable',
                'sortable-options': '{"animation": 150, "ghostClass": "uk-opacity-50", "dragClass": "uk-box-shadow-medium"}',
                'hx-post': f'/checklist/{checklist.id}/reorder-steps',
                'hx-trigger': 'end',
                'hx-target': '#main-content',
                'hx-include': '[name=steps]'
            }),
            
            # Submit button
            DivRAligned(
                Button("Save Changes", 
                       cls=ButtonT.primary,
                       **{
                           'hx-put': f'/checklist/{checklist.id}',
                           'hx-target': '#main-content'
                       })
            ),
            id="edit-checklist-form",
            cls="uk-form-stacked"
        ),
        
        # Add the new step modal
        render_new_step_modal(checklist.id, len(checklist.steps)),
        
        cls="uk-margin",
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


@rt('/checklist/{checklist_id}', methods=['PUT'])
async def put(req):
    checklist_id = int(req.path_params['checklist_id'])
    form = await req.form()
    
    # Get checklist
    checklist = get_checklist_with_steps(checklist_id)
    if not checklist:
        return Div("Checklist not found", cls="uk-alert uk-alert-danger")
    
    # Update checklist details
    result = checklist.update(
        title=form.get('title'),
        description=form.get('description'),
        description_long=form.get('description_long')
    )
    
    # Update steps
    for step in checklist.steps:
        step_result = checklist.update_step(
            step_id=step.id,
            text=form.get(f'step_{step.id}_text'),
            status=form.get(f'step_{step.id}_status'),
            reference_material=form.get(f'step_{step.id}_ref', '')
        )
        result &= step_result
    
    # Return to the checklist view
    return render_checklist_page(checklist_id)

@patch
def update(self:Checklist, title=None, description=None, description_long=None):
    """Update checklist details"""
    with DBConnection() as cursor:
        updates = []
        params = []
        if title is not None:
            updates.append("title = ?")
            params.append(title)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if description_long is not None:
            updates.append("description_long = ?")
            params.append(description_long)
            
        if not updates:
            return False
            
        query = f"""
            UPDATE checklists 
            SET {', '.join(updates)}
            WHERE id = ?
        """
        params.append(self.id)
        cursor.execute(query, params)
        return cursor.rowcount > 0

@patch
def update_step(self:Checklist, step_id, text=None, status=None, reference_material=None):
    """Update a step in the checklist"""
    with DBConnection() as cursor:
        updates = []
        params = []
        if text is not None:
            updates.append("text = ?")
            params.append(text)
        if status is not None:
            updates.append("status = ?")
            params.append(status)
        if reference_material is not None:
            updates.append("reference_material = ?")
            params.append(reference_material)
            
        if not updates:
            return False
            
        query = f"""
            UPDATE steps 
            SET {', '.join(updates)}
            WHERE id = ? AND checklist_id = ?
        """
        params.extend([step_id, self.id])
        cursor.execute(query, params)
        return cursor.rowcount > 0


@rt('/checklist/{checklist_id}/edit')
def get(req):
    checklist_id = int(req.path_params['checklist_id'])
    checklist = get_checklist_with_steps(checklist_id)
    if not checklist:
        return Div("Checklist not found", cls="uk-alert uk-alert-danger")
    return render_checklist_edit(checklist)

### New Routes to handle checklist Edit Features
@rt('/checklist/{checklist_id}/step', methods=['POST'])
async def post(req):
    checklist_id = int(req.path_params['checklist_id'])
    form = await req.form()
    
    # Get form data
    step_text = form.get('step_text', 'New Step')
    step_status = form.get('step_status', 'Not Started')
    step_ref = f'["{form.get("step_ref", "")}"]'  # Format for JSON storage
    position = int(form.get('step_position', 0))
    
    with DBConnection() as cursor:
        # If position specified, shift existing steps
        if position:
            cursor.execute("""
                UPDATE steps 
                SET order_index = order_index + 1
                WHERE checklist_id = ? AND order_index >= ?
            """, (checklist_id, position - 1))
            
            # Insert new step at specified position
            cursor.execute("""
                INSERT INTO steps (checklist_id, text, status, order_index, reference_material)
                VALUES (?, ?, ?, ?, ?)
            """, (checklist_id, step_text, step_status, position - 1, step_ref))
        else:
            # Add to end if no position specified
            cursor.execute("""
                SELECT COALESCE(MAX(order_index), -1) + 1
                FROM steps WHERE checklist_id = ?
            """, (checklist_id,))
            next_order = cursor.fetchone()[0]
            
            cursor.execute("""
                INSERT INTO steps (checklist_id, text, status, order_index, reference_material)
                VALUES (?, ?, ?, ?, ?)
            """, (checklist_id, step_text, step_status, next_order, step_ref))
    
    return render_checklist_edit(get_checklist_with_steps(checklist_id))


@rt('/checklist/{checklist_id}/step/{step_id}', methods=['DELETE'])
async def delete(req):
    checklist_id = int(req.path_params['checklist_id'])
    step_id = int(req.path_params['step_id'])
    
    with DBConnection() as cursor:
        cursor.execute("DELETE FROM steps WHERE id = ? AND checklist_id = ?",
                      (step_id, checklist_id))
    
    return render_checklist_edit(get_checklist_with_steps(checklist_id))

@rt('/checklist/{checklist_id}/reorder-steps', methods=['POST'])
async def post(req):
    checklist_id = int(req.path_params['checklist_id'])
    form = await req.form()
    
    # Get the new order from the form data
    new_order = form.get('steps[]', '').split(',')
    
    with DBConnection() as cursor:
        for i, step_id in enumerate(new_order):
            cursor.execute("""
                UPDATE steps 
                SET order_index = ? 
                WHERE id = ? AND checklist_id = ?
            """, (i, int(step_id), checklist_id))
    
    return render_checklist_edit(get_checklist_with_steps(checklist_id))


if __name__ == '__main__':
    serve()

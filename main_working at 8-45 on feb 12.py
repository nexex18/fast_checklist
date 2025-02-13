import os
from fasthtml.common import *
from fasthtml.common import RedirectResponse as redirect
from monsterui.all import *
from datetime import datetime
import argparse
import json  # For handling reference_material JSON
from fastcore.basics import AttrDict, patch
from instance_functions import (update_instance_step_status, get_instance_step, render_instance_step, render_instance_view_two, render_instances, render_instance_view, get_instance_with_steps, get_filtered_instances,create_new_instance)
from checklist_edit import (
    render_checklist_edit,
    render_new_step_modal,
    render_checklist_header,
    render_checklist_details,
    render_checklist_title_section,
    render_sortable_steps,
    render_step_item,
    render_submit_button,
    update_steps_order
)

from db_connection import DBConnection
import sqlite3
from pathlib import Path

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
    hdrs=Theme.blue.headers(), 
    live=True
)

# UI Components

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
                  cls='uk-link-text uk-text-danger uk-margin-right',
                  **{
                      'hx-delete': f'/checklist/{checklist.id}',
                      'hx-confirm': 'Are you sure you want to delete this checklist?',
                      'hx-target': '#main-content'
                  }),
                A("Instances",
                  cls='uk-link-text uk-text-success',
                  **{
                      'hx-get': f'/instances/{checklist.id}',
                      'hx-target': '#main-content',
                      'hx-push-url': 'true'
                  }),
                cls='uk-flex uk-flex-middle uk-flex-right'
            )
        )
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
            Button("Save & Edit", cls=ButtonT.primary, type="submit", form="new-checklist-form")
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



############ Functions to support Instances Start
def get_instance_with_steps(instance_id):
    """Get a complete instance with all its steps and related information"""
    with DBConnection() as cursor:
        # Get instance details
        cursor.execute("""
            SELECT ci.*, c.title as checklist_title, c.id as checklist_id
            FROM checklist_instances ci
            JOIN checklists c ON ci.checklist_id = c.id
            WHERE ci.id = ?
        """, (instance_id,))
        instance = cursor.fetchone()
        
        if not instance:
            return None
            
        # Get steps with their original text and current status
        cursor.execute("""
            SELECT 
                i_steps.id as instance_step_id,
                i_steps.status,
                i_steps.notes,
                i_steps.updated_at,
                s.text as step_text,
                s.reference_material,
                s.order_index
            FROM instance_steps i_steps
            JOIN steps s ON i_steps.step_id = s.id
            WHERE i_steps.instance_id = ?
            ORDER BY s.order_index
        """, (instance_id,))
        steps = cursor.fetchall()
        
        return AttrDict(
            id=instance['id'],
            checklist_id=instance['checklist_id'],  # Added this line
            name=instance['name'],
            description=instance['description'],
            status=instance['status'],
            created_at=instance['created_at'],
            target_date=instance['target_date'],
            checklist_title=instance['checklist_title'],
            steps=[AttrDict(dict(step)) for step in steps]
        )

def render_instance_view(instance_id):
    """Render a single instance view with basic step status management"""
    instance = get_instance_with_steps(instance_id)
    if not instance:
        return Div("Instance not found", cls="uk-alert uk-alert-danger")
    
    return Div(
        # Header with instance info and parent checklist link
        Div(
            A("← Back to Checklist", 
              cls="uk-link-text", 
              **{'hx-get': f'/checklist/{instance.checklist_id}', 
                 'hx-target': '#main-content'}),
            H2(instance.name, cls="uk-heading-small uk-margin-remove-bottom"),
            P(f"From checklist: {instance.checklist_title}", 
              cls="uk-text-meta uk-margin-remove-top"),
            cls="uk-margin-bottom"
        ),
        
        # Steps list
        Div(*(
            Div(
                # Step text and status in a flex container
                Div(
                    P(step.step_text, cls="uk-margin-remove uk-flex-1"),
                    Select(
                        Option("Not Started", selected=step.status=="Not Started"),
                        Option("In Progress", selected=step.status=="In Progress"),
                        Option("Completed", selected=step.status=="Completed"),
                        cls="uk-select uk-form-small uk-width-small",
                        **{
                            'hx-put': f'/instance-step/{step.instance_step_id}/status',
                            'hx-target': 'closest div'
                        }
                    ),
                    cls="uk-flex uk-flex-middle uk-flex-between"
                ),
                cls="uk-margin-medium-bottom uk-padding-small uk-box-shadow-small"
            )
            for step in instance.steps
        )),
        
        id="main-content",
        cls="uk-container uk-margin-top"
    )


############ Functions to support Instances End

# Routes
@rt('/')
async def get(req):
    return render_main_page()

@rt('/create')
async def post(req):
    form = await req.form()
    try:
        checklist = Checklist(
            id=None,
            title=form['title'],
            description=form.get('description', ''),
            description_long='',
            created_at=datetime.now().isoformat(),
            steps=[]
        )
        checklist_data = dict(checklist)
        del checklist_data['steps']
        del checklist_data['id']
        
        # Insert using DBConnection
        with DBConnection() as cursor:
            cursor.execute("""
                INSERT INTO checklists (title, description, description_long, created_at)
                VALUES (?, ?, ?, ?)
            """, (
                checklist_data['title'],
                checklist_data['description'],
                checklist_data['description_long'],
                checklist_data['created_at']
            ))
            cursor.execute("SELECT last_insert_rowid()")
            new_id = cursor.fetchone()[0]
        
        return RedirectResponse(f'/checklist/{new_id}/edit', status_code=303)
            
    except Exception as e:
        print(f"Error creating checklist: {e}")
        raise

@rt('/checklist/{checklist_id}')
def get(req):
    checklist_id = int(req.path_params['checklist_id'])
    return render_checklist_page(checklist_id)  # Now passing the parameter

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

### Routes to handle checklist Edit Features
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
    
    print("DEBUG - Received form data:", dict(form))
    
    # Get ordered step IDs from the form data
    step_ids = [int(id) for id in form.getlist('step_order[]')]
    
    print("DEBUG - Processed step IDs:", step_ids)
    
    if step_ids:
        update_steps_order(checklist_id, step_ids)
    
    return render_checklist_edit(get_checklist_with_steps(checklist_id))


### Instance related routes
@rt('/instances/{checklist_id}')
def get(req):
    checklist_id = int(req.path_params['checklist_id'])
    return render_instances(checklist_id=checklist_id)

@rt('/instance/{instance_id}')
def get(req):
    instance_id = int(req.path_params['instance_id'])
    return render_instance_view_two(instance_id)

@rt('/instance/create')
async def post(req):
    form = await req.form()
    checklist_id = int(form['checklist_id'])
    instance_id = create_new_instance(
        checklist_id=checklist_id,
        name=form['name'],
        description=form.get('description'),
        target_date=form.get('target_date')
    )
    return render_instances(checklist_id=checklist_id)

@rt('/instance-step/{step_id}/status', methods=['PUT'])
async def put(req):
    step_id = int(req.path_params['step_id'])
    form = await req.form()
    new_status = form.get('status')
    
    if update_instance_step_status(step_id, new_status):
        step = get_instance_step(step_id)
        if step:
            return render_instance_step(step)
    
    return "Error updating step status", 400

if __name__ == '__main__':
    serve()

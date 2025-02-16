from fasthtml.common import * 
from datetime import datetime
from db_connection import DBConnection
from checklist_list import render_main_page, get_checklist_with_steps, render_checklist_page
from checklist_edit import (
    render_checklist_edit, render_sortable_steps, render_step_item, 
    render_step_text, render_step_reference, db_update_step,
    get_step, get_step_reference, update_step_reference, validate_url
)

from instance_functions import (
    render_instances, render_instance_view_two, create_new_instance,
    update_instance_step_status, get_instance_step, render_instance_step
)

from models import Checklist

from main import *

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
async def put(req, id:list[int]):  # Add explicit parameter expectation
    checklist_id = int(req.path_params['checklist_id'])
    print(f"DEBUG: PUT endpoint - Received IDs: {id}")  # Debug print
    
    # Update the order
    if id:  # If we have IDs
        with DBConnection() as cursor:
            for i, step_id in enumerate(id):
                cursor.execute("""
                    UPDATE steps 
                    SET order_index = ? 
                    WHERE id = ? AND checklist_id = ?
                """, (i, step_id, checklist_id))
    
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
    print(f"DEBUG: Creating new step - Form data: {dict(form)}") 

    with DBConnection() as cursor:
        # Get the maximum order_index for this checklist
        cursor.execute("""
            SELECT COALESCE(MAX(order_index), -1) + 1
            FROM steps WHERE checklist_id = ?
        """, (checklist_id,))
        next_order = cursor.fetchone()[0]
        
        # Always insert at the end
        cursor.execute("""
            INSERT INTO steps (checklist_id, text, status, order_index, reference_material)
            VALUES (?, ?, ?, ?, ?)
        """, (
            checklist_id,
            form.get('step_text', 'New Step'),
            form.get('step_status', 'Not Started'),
            next_order,  # Use the next available order_index
            f'["{form.get("step_ref", "")}"]'
        ))
    
    return render_checklist_edit(get_checklist_with_steps(checklist_id))

@rt('/checklist/{checklist_id}/step/{step_id}', methods=['DELETE'])
async def delete(req):
    checklist_id = int(req.path_params['checklist_id'])
    step_id = int(req.path_params['step_id'])
    
    with DBConnection() as cursor:
        cursor.execute("DELETE FROM steps WHERE id = ? AND checklist_id = ?",
                      (step_id, checklist_id))
    
    return render_checklist_edit(get_checklist_with_steps(checklist_id))

# Route handler for reordering (for completeness)
@rt('/checklist/{checklist_id}/reorder-steps', methods=['POST'])
async def post(req, id:list[int]):
    checklist_id = int(req.path_params['checklist_id'])
    print("DEBUG: ====== REORDER ENDPOINT HIT ======")
    print(f"DEBUG: Reordering steps - Received IDs: {id}")
    
    with DBConnection() as cursor:
        # First, verify all steps belong to this checklist
        step_ids = ','.join('?' * len(id))
        cursor.execute(f"""
            SELECT COUNT(*) 
            FROM steps 
            WHERE checklist_id = ? AND id IN ({step_ids})
        """, (checklist_id, *id))
        
        if cursor.fetchone()[0] != len(id):
            return "Invalid step IDs", 400
            
        # Update all positions in a transaction
        for i, step_id in enumerate(id):
            cursor.execute("""
                UPDATE steps 
                SET order_index = ? 
                WHERE id = ? AND checklist_id = ?
            """, (i, step_id, checklist_id))
    
    # Return the updated list
    checklist = get_checklist_with_steps(checklist_id)
    return render_sortable_steps(checklist)

@rt('/checklist/{checklist_id}/step/{step_id}', methods=['PUT'])
async def put(req):
    """Handle individual step updates (text or reference changes)"""
    try:
        checklist_id = int(req.path_params['checklist_id'])
        step_id = int(req.path_params['step_id'])
        form = await req.form()
        
        print(f"Raw form data: {dict(form)}")  # Debug log
        
        # Verify we're updating the correct step
        form_step_id = form.get('step_id')
        if form_step_id and int(form_step_id) != step_id:
            print(f"ID mismatch: form={form_step_id}, url={step_id}")
            return "Invalid step ID", 400
        
        # Process form data
        updates = {}
        if 'step_text' in form:
            new_text = form['step_text'].strip()
            if new_text != '':  # Only update if there's actual text
                updates['text'] = new_text
                
        if 'reference_material' in form:
            ref_material = form['reference_material'].strip()
            if ref_material:  # Only update if there's a reference
                updates['reference_material'] = f'["{ref_material}"]'
            
        print(f"Processing updates: {updates}")  # Debug log
        
        if not updates:
            return "No valid updates provided", 400
            
        # Update and get refreshed step
        step = db_update_step(checklist_id, step_id, **updates)
        if not step:
            return "Step not found or update failed", 404
        
        print(f"Updated step: {step}")  # Debug log
        
        # Return appropriate render based on what was updated
        if 'text' in updates and 'reference_material' in updates:
            return render_step_item(step, checklist_id, step.order_index + 1)
        elif 'text' in updates:
            return render_step_text(step, checklist_id)
        else:
            return render_step_reference(step, checklist_id)
            
    except ValueError as e:
        print(f"Validation error: {e}")
        return f"Invalid input: {str(e)}", 400
    except Exception as e:
        print(f"Unexpected error: {e}")
        return "Server error", 500

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

@rt('/step/{step_id}/reference', methods=['PUT'])
async def put(req, step_id: int, url: str):
    """Handle reference URL updates"""
    is_valid, error = validate_url(url)
    if not is_valid:
        return error, 400
        
    ref = update_step_reference(step_id, url)
    if ref:
        step = get_step(step_id)  # Now works without checklist_id
        return render_step_reference(step, None)
    return "Error updating reference", 400


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





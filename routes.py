from fasthtml.common import * 
from datetime import datetime
from db_connection import DBConnection
from checklist_list import render_main_page, get_checklist_with_steps, render_checklist_page

from checklist_edit import (
    render_checklist_edit, render_sortable_steps, render_step_item, 
    render_step_text, render_step_reference, db_update_step,
    get_step, get_step_reference, update_step_reference, validate_url,
    create_new_step, update_checklist_field, render_checklist_field  # Add this line
)


from instance_functions import (
    render_instances, render_instance_view, create_new_instance,
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


@rt('/checklist/{checklist_id}/step', methods=['POST'])
async def post(req):
    """Create a new step and optionally its reference"""
    checklist_id = int(req.path_params['checklist_id'])
    form = await req.form()
    
    try:
        # Get form data
        position = int(form.get('step_position', 1))
        text = form.get('step_text', 'New Step')
        reference_url = form.get('step_ref', '').strip()
        
        # Create step using the new function
        step_id, ref_error = create_new_step(
            checklist_id=checklist_id,
            text=text,
            position=position,
            reference_url=reference_url if reference_url else None
        )
        
        # Get updated checklist for rendering
        checklist = get_checklist_with_steps(checklist_id)
        if ref_error:
            return render_checklist_edit(checklist), f"Step created but reference invalid: {ref_error}", 400
        return render_sortable_steps(checklist) #render_checklist_edit(checklist)
            
    except Exception as e:
        return f"Error creating step: {str(e)}", 500



@rt('/checklist/{checklist_id}/step/{step_id}', methods=['DELETE'])
async def delete(req):
    checklist_id = int(req.path_params['checklist_id'])
    step_id = int(req.path_params['step_id'])
    
    with DBConnection() as cursor:
        cursor.execute("DELETE FROM steps WHERE id = ? AND checklist_id = ?",
                      (step_id, checklist_id))
    
    return render_checklist_edit(get_checklist_with_steps(checklist_id))




@rt('/step/{step_id}/reference', methods=['PUT'])
async def put(req, step_id: int):
    """Handle reference URL updates"""
    form = await req.form()
    url = form.get('url', '').strip()
    print(f"DEBUG: Received form data: {dict(form)}")
    print(f"DEBUG: Parsed URL: '{url}'")
    
    # Get step first to ensure it exists
    step = get_step(step_id)
    if not step:
        print(f"DEBUG: Step {step_id} not found")
        return render_step_reference(step, None, error="Step not found")
        
    # Validate URL
    is_valid, error = validate_url(url)
    print(f"DEBUG: URL validation - Valid: {is_valid}, Error: {error}")
    
    if not is_valid:
        return render_step_reference(step, None, error=error)
        
    # Update reference
    ref = update_step_reference(step_id, url)
    print(f"DEBUG: Updated reference result: {dict(ref) if ref else None}")
    
    return render_step_reference(step, None)

@rt('/checklist/{checklist_id}/field/{field_name}', methods=['PUT'])
async def put(req):
    """Handle individual field updates"""
    try:
        checklist_id = int(req.path_params['checklist_id'])
        field_name = req.path_params['field_name']
        form = await req.form()
        
        # Get form field value using the same pattern as render function
        input_id = f"{field_name}_text"
        if input_id not in form:
            return "Missing field value", 400
            
        new_value = form[input_id].strip()
        if not new_value:
            return "Empty value not allowed", 400
            
        # Update and get refreshed checklist
        checklist = update_checklist_field(checklist_id, field_name, new_value)
        if not checklist:
            return "Update failed", 404
            
        # Return the updated field component
        return render_checklist_field(
            checklist.id, 
            field_name,
            getattr(checklist, field_name),
            field_name.replace('_', ' ').title(),
            "textarea" if field_name == "description_long" else "input"
        )
            
    except Exception as e:
        print(f"Error updating field: {e}")
        return "Server error", 500


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
    """Handle individual step updates (text changes only)"""
    try:
        checklist_id = int(req.path_params['checklist_id'])
        step_id = int(req.path_params['step_id'])
        form = await req.form()
        
        # Process form data - now only handling text updates
        updates = {}
        if 'step_text' in form:
            new_text = form['step_text'].strip()
            if new_text != '':  # Only update if there's actual text
                updates['text'] = new_text
        
        if not updates:
            return "No valid updates provided", 400
            
        # Update and get refreshed step
        step = db_update_step(checklist_id, step_id, **updates)
        if not step:
            return "Step not found or update failed", 404
        
        # Return appropriate render based on what was updated
        return render_step_text(step, checklist_id)
            
    except ValueError as e:
        print(f"Validation error: {e}")
        return f"Invalid input: {str(e)}", 400
    except Exception as e:
        print(f"Unexpected error: {e}")
        return "Server error", 500

### Instance related routes
@rt('/checklist/{checklist_id}/instances')
def get(req):
    checklist_id = int(req.path_params['checklist_id'])
    return render_instances(checklist_id=checklist_id)

@rt('/checklist/{checklist_id}/instance/{instance_id}')
def get(req):
    checklist_id = int(req.path_params['checklist_id'])
    instance_id = int(req.path_params['instance_id'])
    return render_instance_view(instance_id)

@rt('/checklist/{checklist_id}/instance/create')
async def post(req):
    checklist_id = int(req.path_params['checklist_id'])
    form = await req.form()
    instance_id = create_new_instance(
        checklist_id=checklist_id,
        name=form['name'],
        description=form.get('description'),
        target_date=form.get('target_date')
    )
    return render_instances(checklist_id=checklist_id)

@rt('/checklist/{checklist_id}/instance/{instance_id}/step/{step_id}/status', methods=['PUT'])
async def put(req):
    checklist_id = int(req.path_params['checklist_id'])
    instance_id = int(req.path_params['instance_id'])
    step_id = int(req.path_params['step_id'])
    form = await req.form()
    new_status = form.get('status')
    
    if update_instance_step_status(step_id, new_status):
        step = get_instance_step(step_id)
        if step:
            return render_instance_step(step)
    
    return "Error updating step status", 400


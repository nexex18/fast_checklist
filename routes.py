from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from datetime import datetime
from db_connection import DBConnection
from models import Checklist
from checklist_list import render_main_page, get_checklist_with_steps, render_checklist_page
from checklist_edit import (
    render_checklist_edit, render_sortable_steps, render_step_item, 
    render_step_text, render_step_reference, db_update_step
)
from instance_functions import (
    render_instances, render_instance_view_two, create_new_instance,
    update_instance_step_status, get_instance_step, render_instance_step
)

router = APIRouter()

# Base routes
@router.get('/')
async def get(req: Request):
    return render_main_page()

@router.post('/create')
async def post(req: Request):
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

# Checklist routes
@router.get('/checklist/{checklist_id}')
def get(req: Request):
    checklist_id = int(req.path_params['checklist_id'])
    return render_checklist_page(checklist_id)

@router.delete('/checklist/{checklist_id}')
async def delete(req: Request):
    checklist_id = int(req.path_params['checklist_id'])
    checklist = get_checklist_with_steps(checklist_id)
    if checklist:
        checklist.delete()
    return render_main_page()

@router.put('/checklist/{checklist_id}')
async def put(req: Request, id: list[int]):
    checklist_id = int(req.path_params['checklist_id'])
    print(f"DEBUG: PUT endpoint - Received IDs: {id}")
    
    if id:
        with DBConnection() as cursor:
            for i, step_id in enumerate(id):
                cursor.execute("""
                    UPDATE steps 
                    SET order_index = ? 
                    WHERE id = ? AND checklist_id = ?
                """, (i, step_id, checklist_id))
    
    return render_checklist_page(checklist_id)

@router.get('/checklist/{checklist_id}/edit')
def get(req: Request):
    checklist_id = int(req.path_params['checklist_id'])
    checklist = get_checklist_with_steps(checklist_id)
    if not checklist:
        return Div("Checklist not found", cls="uk-alert uk-alert-danger")
    return render_checklist_edit(checklist)

# Step routes
@router.post('/checklist/{checklist_id}/step')
async def post(req: Request):
    checklist_id = int(req.path_params['checklist_id'])
    form = await req.form()
    print(f"DEBUG: Creating new step - Form data: {dict(form)}")

    with DBConnection() as cursor:
        cursor.execute("""
            SELECT COALESCE(MAX(order_index), -1) + 1
            FROM steps WHERE checklist_id = ?
        """, (checklist_id,))
        next_order = cursor.fetchone()[0]
        
        cursor.execute("""
            INSERT INTO steps (checklist_id, text, status, order_index, reference_material)
            VALUES (?, ?, ?, ?, ?)
        """, (
            checklist_id,
            form.get('step_text', 'New Step'),
            form.get('step_status', 'Not Started'),
            next_order,
            f'["{form.get("step_ref", "")}"]'
        ))
    
    return render_checklist_edit(get_checklist_with_steps(checklist_id))

@router.delete('/checklist/{checklist_id}/step/{step_id}')
async def delete(req: Request):
    checklist_id = int(req.path_params['checklist_id'])
    step_id = int(req.path_params['step_id'])
    
    with DBConnection() as cursor:
        cursor.execute("DELETE FROM steps WHERE id = ? AND checklist_id = ?",
                      (step_id, checklist_id))
    
    return render_checklist_edit(get_checklist_with_steps(checklist_id))

@router.post('/checklist/{checklist_id}/reorder-steps')
async def post(req: Request, id: list[int]):
    checklist_id = int(req.path_params['checklist_id'])
    print("DEBUG: ====== REORDER ENDPOINT HIT ======")
    print(f"DEBUG: Reordering steps - Received IDs: {id}")
    
    with DBConnection() as cursor:
        step_ids = ','.join('?' * len(id))
        cursor.execute(f"""
            SELECT COUNT(*) 
            FROM steps 
            WHERE checklist_id = ? AND id IN ({step_ids})
        """, (checklist_id, *id))
        
        if cursor.fetchone()[0] != len(id):
            return "Invalid step IDs", 400
            
        for i, step_id in enumerate(id):
            cursor.execute("""
                UPDATE steps 
                SET order_index = ? 
                WHERE id = ? AND checklist_id = ?
            """, (i, step_id, checklist_id))
    
    checklist = get_checklist_with_steps(checklist_id)
    return render_sortable_steps(checklist)

@router.put('/checklist/{checklist_id}/step/{step_id}')
async def put(req: Request):
    try:
        checklist_id = int(req.path_params['checklist_id'])
        step_id = int(req.path_params['step_id'])
        form = await req.form()
        
        print(f"Raw form data: {dict(form)}")
        
        form_step_id = form.get('step_id')
        if form_step_id and int(form_step_id) != step_id:
            print(f"ID mismatch: form={form_step_id}, url={step_id}")
            return "Invalid step ID", 400
        
        updates = {}
        if 'step_text' in form:
            new_text = form['step_text'].strip()
            if new_text != '':
                updates['text'] = new_text
                
        if 'reference_material' in form:
            ref_material = form['reference_material'].strip()
            if ref_material:
                updates['reference_material'] = f'["{ref_material}"]'
            
        print(f"Processing updates: {updates}")
        
        if not updates:
            return "No valid updates provided", 400
            
        step = db_update_step(checklist_id, step_id, **updates)
        if not step:
            return "Step not found or update failed", 404
        
        print(f"Updated step: {step}")
        
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

# Instance routes
@router.get('/instances/{checklist_id}')
def get(req: Request):
    checklist_id = int(req.path_params['checklist_id'])
    return render_instances(checklist_id=checklist_id)

@router.get('/instance/{instance_id}')
def get(req: Request):
    instance_id = int(req.path_params['instance_id'])
    return render_instance_view_two(instance_id)

@router.post('/instance/create')
async def post(req: Request):
    form = await req.form()
    checklist_id = int(form['checklist_id'])
    instance_id = create_new_instance(
        checklist_id=checklist_id,
        name=form['name'],
        description=form.get('description'),
        target_date=form.get('target_date')
    )
    return render_instances(checklist_id=checklist_id)

@router.put('/instance-step/{step_id}/status')
async def put(req: Request):
    step_id = int(req.path_params['step_id'])
    form = await req.form()
    new_status = form.get('status')
    
    if update_instance_step_status(step_id, new_status):
        step = get_instance_step(step_id)
        if step:
            return render_instance_step(step)
    
    return "Error updating step status", 400
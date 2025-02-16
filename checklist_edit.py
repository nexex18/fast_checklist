from fasthtml.common import *
from fasthtml.components import *
from monsterui.all import *
from datetime import datetime
from fastcore.basics import AttrDict
from db_connection import DBConnection

from models import Checklist

from urllib.parse import urlparse

### Data access functions
def update_steps_order(checklist_id: int, step_ids: list):
    """Update the order_index of steps in a checklist"""
    with DBConnection() as cursor:
        for i, step_id in enumerate(step_ids):
            cursor.execute("""
                UPDATE steps 
                SET order_index = ? 
                WHERE id = ? AND checklist_id = ?
            """, (i, int(step_id), checklist_id))
    return True



def db_update_step(checklist_id: int, step_id: int, **updates):
    """Update step fields in database and return updated step"""
    if not updates:
        return None
    
    # Only allow text and status updates
    allowed_fields = {'text', 'status'}
    valid_updates = {k: v for k, v in updates.items() if k in allowed_fields}
    
    if not valid_updates:
        return None
        
    with DBConnection() as cursor:
        set_clause = ', '.join(f"{k} = ?" for k in valid_updates)
        params = list(valid_updates.values())
        params.extend([step_id, checklist_id])
        
        cursor.execute(f"""
            UPDATE steps 
            SET {set_clause}
            WHERE id = ? AND checklist_id = ?
        """, params)
        
        # Get updated step
        cursor.execute("""
            SELECT * FROM steps 
            WHERE id = ? AND checklist_id = ?
        """, (step_id, checklist_id))
        return AttrDict(cursor.fetchone())


def get_step_reference(step_id: int):
    """Get reference URL for a step"""
    with DBConnection() as cursor:
        cursor.execute("""
            SELECT sr.id, sr.url, sr.type_id
            FROM step_references sr
            WHERE sr.step_id = ?
        """, (step_id,))
        row = cursor.fetchone()
        return AttrDict(row) if row else None

def update_step_reference(step_id: int, url: str, type_id: int = 1):
    """Create or update a reference URL for a step"""
    with DBConnection() as cursor:
        cursor.execute("""
            INSERT INTO step_references (step_id, url, type_id)
            VALUES (?, ?, ?)
            ON CONFLICT(step_id) DO UPDATE SET
                url = excluded.url,
                type_id = excluded.type_id
            RETURNING *
        """, (step_id, url, type_id))
        return get_step_reference(step_id)


def get_step(step_id: int, checklist_id: int = None):
    """Get a single step with its reference"""
    with DBConnection() as cursor:
        query = """
            SELECT 
                s.id, s.checklist_id, s.text, s.status, s.order_index,
                sr.url as reference_url, sr.type_id as reference_type_id
            FROM steps s
            LEFT JOIN step_references sr ON s.id = sr.step_id
            WHERE s.id = ?
        """
        params = [step_id]
        if checklist_id is not None:
            query += " AND s.checklist_id = ?"
            params.append(checklist_id)
            
        cursor.execute(query, params)
        row = cursor.fetchone()
        return AttrDict(row) if row else None


def validate_url(url: str) -> tuple[bool, str]:
    """Validate URL and return (is_valid, error_message)"""
    if not url:
        return False, "URL cannot be empty"
    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            return False, "URL must include scheme (http:// or https://) and domain"
        if result.scheme not in ['http', 'https']:
            return False, "URL must use http or https"
        return True, ""
    except Exception as e:
        return False, f"Invalid URL format: {str(e)}"



# UI Components - rendering functions

def render_checklist_header(checklist_id):
    return Div(
        A("← Back", 
          cls="uk-link-text", 
          **{'hx-get': f'/checklist/{checklist_id}', 
             'hx-target': '#main-content'}),
        cls="uk-margin-bottom"
    )

def render_checklist_title_section(checklist_id):
    """Render the title section with add step button"""
    return Div(
        H2("Edit Checklist", cls="uk-heading-small uk-margin-remove"),
        A("➕",
          cls="uk-link-muted uk-button uk-button-small",
          **{'uk-toggle': 'target: #new-step-modal'}),
        cls="uk-flex uk-flex-middle uk-flex-between uk-margin-bottom"
    )

def render_checklist_details(checklist):
    return [
        LabelInput("Title", 
                  id="title", 
                  value=checklist.title,
                  cls="uk-margin-small"),
        LabelInput("Description", 
                  id="description",
                  value=checklist.description,
                  cls="uk-margin-small"),
        LabelTextArea("Long Description", 
                     id="description_long",
                     value=checklist.description_long,
                     cls="uk-margin-small")
    ]

def render_submit_button(checklist_id):
    return Button(
        "Save Changes", 
        cls="uk-button uk-button-primary uk-margin-top",
        **{
            'hx-put': f'/checklist/{checklist_id}',
            'hx-target': '#main-content',
            'hx-include': '.sortable *'  # Include all elements inside sortable
        }
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
    """Main wrapper function that composes all components"""
    return Div(
        # Header
        render_checklist_header(checklist.id),
        
        # Main Form
        Form(
            render_checklist_title_section(checklist.id),
            *render_checklist_details(checklist),  # Added asterisk to unpack the list
            render_sortable_steps(checklist),
            render_submit_button(checklist.id),
            id="edit-checklist-form",
            cls="uk-form-stacked"
        ),
        
        SortableJS('.sortable', ghost_class='blue-background-class'),
        render_new_step_modal(checklist.id, len(checklist.steps)),
        cls="uk-margin",
        id="main-content"
    )

def render_step_text(step, checklist_id):
    """Render just the text input portion"""
    return Div(
        Form(  # Wrap in a form to isolate the data being sent
            LabelInput(label="", 
                      id=f"step_{step.id}_text",
                      name="step_text",
                      value=step.text,
                      cls="uk-width-1-1"),
            Hidden(name="step_id", value=step.id),  # Add hidden field for correct ID
            **{
                'hx-put': f'/checklist/{checklist_id}/step/{step.id}',
                'hx-trigger': 'change',
                'hx-target': f'#step-text-{step.id}',
                'hx-swap': 'outerHTML'
            }
        ),
        A("🗑️",
          cls="uk-link-danger uk-margin-small-left",
          **{
              'hx-delete': f'/checklist/{checklist_id}/step/{step.id}',
              'hx-confirm': 'Are you sure you want to delete this step?',
              'hx-target': '#main-content'
          }),
        cls="uk-flex uk-flex-middle",
        id=f"step-text-{step.id}"
    )

def render_step_reference(step, checklist_id):
    """Render just the reference input portion"""
    ref = get_step_reference(step.id)
    return LabelInput(
        label="Reference URL",
        id=f"step_{step.id}_ref",
        name="url",
        value=ref.url if ref else "",  # Just use the URL value
        cls="uk-width-1-1 uk-margin-small-top",
        **{
            'hx-put': f'/step/{step.id}/reference',
            'hx-trigger': 'change',
            'hx-target': 'closest div'
        }
    )


def render_step_item(step, checklist_id, step_number):
    print(f"DEBUG: Rendering step item - ID: {step.id}, Order: {step.order_index}")
    return Div(
        Div(
            Span("⋮⋮", 
                 cls="uk-margin-small-right drag-handle", 
                 style="cursor: move"),
            Span(f"Step {step_number}", 
                 cls="uk-form-label"),
            Div(
                render_step_text(step, checklist_id),
                render_step_reference(step, checklist_id),
                cls="uk-width-expand"
            ),
            cls="uk-flex"
        ),
        # Add the hidden input here, at the Div level
        Hidden(name="id", value=step.id),  # This is the key addition
        cls="uk-padding-small uk-margin-small uk-box-shadow-small",
        **{
            'data-id': step.id,  # Keep this for SortableJS
            'data-order': step.order_index,  # Keep this for reference
            'name': 'steps'  # Keep this for form structure
        }
    )

def render_sortable_steps(checklist):
    return Form(
        H3("Steps", cls="uk-heading-small uk-margin-top"),
        Ul(*(
            Li(
                render_step_item(step, checklist.id, idx+1),
                # Remove the Hidden input here since it's in render_step_item
                id=f'step-{step.id}',
                cls="uk-padding-small uk-margin-small uk-box-shadow-small"
            )
            for idx, step in enumerate(checklist.steps)
        ), cls='sortable'),
        Hidden(name="step_order", value=",".join(str(step.id) for step in checklist.steps)),
        id='steps-list',
        hx_post=f'/checklist/{checklist.id}/reorder-steps',
        hx_trigger="end"
    )
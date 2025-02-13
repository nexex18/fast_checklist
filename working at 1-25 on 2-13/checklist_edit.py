from fasthtml.common import *
from fasthtml.components import *
from monsterui.all import *
from datetime import datetime
from fastcore.basics import AttrDict
from db_connection import DBConnection


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

def render_step_item(step, checklist_id, step_number):
    """Render a single step item with its controls"""
    return Div(
        Div(
            # Left column for handle and step number
            Span("⋮⋮", cls="uk-margin-small-right drag-handle", style="cursor: move"),
            Span(f"Step {step_number}", cls="uk-form-label"),
            
            # Right column for form fields
            Div(
                # Text input and delete button
                Div(
                    LabelInput(label="", 
                             id=f"step_{step.id}_text",
                             value=step.text,
                             cls="uk-width-1-1"),
                    A("🗑️",
                      cls="uk-link-danger uk-margin-small-left",
                      **{
                          'hx-delete': f'/checklist/{checklist_id}/step/{step.id}',
                          'hx-confirm': 'Are you sure you want to delete this step?',
                          'hx-target': '#main-content'
                      }),
                    cls="uk-flex uk-flex-middle"
                ),
                # Reference field
                LabelInput(label="Reference Material",
                         id=f"step_{step.id}_ref",
                         value=step.reference_material.strip('"[]') if step.reference_material else "",
                         cls="uk-width-1-1 uk-margin-small-top"),
                cls="uk-width-expand"
            ),
            cls="uk-flex"
        ),
        cls="uk-padding-small uk-margin-small uk-box-shadow-small",
        **{
            'data-id': step.id,
            'name': 'steps'
        }
    )


## After making many changes to render_sortable_steps it's still not working
## This is the current state. 
def render_sortable_steps(checklist):
    return Form(
        H3("Steps", cls="uk-heading-small uk-margin-top"),
        Ul(*(
            Li(
                render_step_item(step, checklist.id, idx+1),
                Hidden(name="id", value=step.id),
                id=f'step-{step.id}',
                cls="uk-padding-small uk-margin-small uk-box-shadow-small"
            )
            for idx, step in enumerate(checklist.steps)
        ), cls='sortable'),
        id='steps-list',
        hx_post=f'/checklist/{checklist.id}/reorder-steps',
        hx_trigger="end"
    )


def render_submit_button(checklist_id):
    """Render the save changes button with order capture"""
    return Button(
        "Save Changes", 
        cls="uk-button uk-button-primary uk-margin-top",
        **{
            'hx-put': f'/checklist/{checklist_id}',
            'hx-target': '#main-content',
            'onclick': '''
                let order = Array.from(document.querySelector('.sortable').children)
                    .map(el => el.dataset.id);
                let orderInput = document.createElement('input');
                orderInput.type = 'hidden';
                orderInput.name = 'step_order';
                orderInput.value = order.join(',');
                this.form.appendChild(orderInput);
            '''
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

### function support route 
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




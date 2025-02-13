from fasthtml.common import *
from fasthtml.components import *
from monsterui.all import *
from datetime import datetime
from fastcore.basics import AttrDict
from db_connection import DBConnection


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
        # Header
        Div(
            A("← Back", 
              cls="uk-link-text", 
              **{'hx-get': f'/checklist/{checklist.id}', 
                 'hx-target': '#main-content'}),
            cls="uk-margin-bottom"
        ),
        
        # Main Form
        Form(
            # Title section
            Div(
                H2("Edit Checklist", cls="uk-heading-small uk-margin-remove"),
                A("➕",
                  cls="uk-link-muted uk-button uk-button-small",
                  **{'uk-toggle': 'target: #new-step-modal'}),
                cls="uk-flex uk-flex-middle uk-flex-between uk-margin-bottom"
            ),
            
            # Checklist details
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
                         cls="uk-margin-small"),

            # Sortable steps section
            H3("Steps", cls="uk-heading-small uk-margin-top"),
            Div(*(
                Div(
                    Div(
                        # Left column for handle and step number
                        Span("⋮⋮", cls="uk-margin-small-right drag-handle", style="cursor: move"),
                        Span(f"Step {i+1}", cls="uk-form-label"),
                        
                        # Right column for all form fields
                        Div(
                            # Top row with text input and delete
                            Div(
                                LabelInput(label="", 
                                         id=f"step_{step.id}_text",
                                         value=step.text,
                                         cls="uk-width-1-1"),
                                A("🗑️",
                                  cls="uk-link-danger uk-margin-small-left",
                                  **{
                                      'hx-delete': f'/checklist/{checklist.id}/step/{step.id}',
                                      'hx-confirm': 'Are you sure you want to delete this step?',
                                      'hx-target': '#main-content'
                                  }),
                                cls="uk-flex uk-flex-middle"
                            ),
                            # Reference Material field
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
                for i, step in enumerate(checklist.steps)
            ),
            id='sortable-steps',
            cls="sortable",
            **{
                'hx-post': f'/checklist/{checklist.id}/reorder-steps',
                'hx-trigger': 'end',
                'hx-target': '#main-content',
                'hx-include': '[name=steps]',
                'sortable-options': '{"animation": 150, "ghostClass": "uk-opacity-50", "dragClass": "uk-box-shadow-medium"}'
            }),
            
            # Submit button
            Button("Save Changes", 
                   cls="uk-button uk-button-primary uk-margin-top",
                   **{
                       'hx-put': f'/checklist/{checklist.id}',
                       'hx-target': '#main-content'
                   }),
            id="edit-checklist-form",
            cls="uk-form-stacked"
        ),
        
        SortableJS('.sortable', ghost_class='blue-background-class'),
        render_new_step_modal(checklist.id, len(checklist.steps)),  # Added new step modal
        cls="uk-margin",
        id="main-content"
    )

from fasthtml.common import *
from fasthtml.components import *
from monsterui.all import *
from datetime import datetime
from fastcore.basics import AttrDict
from db_connection import DBConnection

# Your instance functions here...

# Data access functions
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
            checklist_id=instance['checklist_id'],
            name=instance['name'],
            description=instance['description'],
            status=instance['status'],
            created_at=instance['created_at'],
            target_date=instance['target_date'],
            checklist_title=instance['checklist_title'],
            steps=[AttrDict(dict(step)) for step in steps]
        )

def get_filtered_instances(checklist_id=None, status=None):
    """Get instances with optional filtering"""
    with DBConnection() as cursor:
        query = """
            SELECT 
                ci.id,
                ci.name,
                ci.status,
                ci.created_at,
                ci.target_date,
                c.title as checklist_title,
                c.id as checklist_id,
                (
                    SELECT COUNT(*) 
                    FROM instance_steps 
                    WHERE instance_id = ci.id AND status = 'Completed'
                ) as completed_steps,
                (
                    SELECT COUNT(*) 
                    FROM instance_steps 
                    WHERE instance_id = ci.id
                ) as total_steps
            FROM checklist_instances ci
            JOIN checklists c ON ci.checklist_id = c.id
            WHERE 1=1
        """
        params = []
        
        if checklist_id is not None:
            query += " AND c.id = ?"
            params.append(checklist_id)
            
        if status is not None:
            query += " AND ci.status = ?"
            params.append(status)
            
        query += " ORDER BY ci.created_at DESC"
        
        cursor.execute(query, params)
        instances = cursor.fetchall()
        return [AttrDict(dict(instance)) for instance in instances]

def create_instance_modal(checklist_id):
    """Create the modal for new instance creation"""
    return Modal(
        ModalTitle("Create New Instance"),
        ModalBody(
            Form(
                LabelInput("Name", id="name", placeholder="Instance Name", required=True),
                LabelTextArea("Description", id="description", placeholder="Optional description"),
                LabelInput("Target Date", id="target_date", type="date"),
                Hidden(id="checklist_id", value=str(checklist_id)),
                action=f"/instance/create",
                method="POST",
                id="new-instance-form"
            )
        ),
        footer=DivRAligned(
            ModalCloseButton("Cancel", cls=ButtonT.default),
            Button("Create", 
                  cls=ButtonT.primary, 
                  type="submit",
                  form="new-instance-form")
        ),
        id='new-instance-modal'
    )

def create_new_instance(checklist_id, name, description=None, target_date=None):
    """Create a new instance and its steps from a checklist"""
    with DBConnection() as cursor:
        # Insert the new instance
        cursor.execute("""
            INSERT INTO checklist_instances 
            (checklist_id, name, description, status, created_at, target_date)
            VALUES (?, ?, ?, 'Not Started', datetime('now'), ?)
        """, (checklist_id, name, description, target_date))
        instance_id = cursor.lastrowid
        
        # Copy steps from checklist to instance
        cursor.execute("""
            INSERT INTO instance_steps 
            (instance_id, step_id, status, updated_at)
            SELECT ?, id, 'Not Started', datetime('now')
            FROM steps 
            WHERE checklist_id = ?
            ORDER BY order_index
        """, (instance_id, checklist_id))
        
        return instance_id

def get_instance_step(step_id):
    """Get a single instance step with its details"""
    with DBConnection() as cursor:
        cursor.execute("""
            SELECT i_steps.*, s.text as step_text
            FROM instance_steps i_steps
            JOIN steps s ON i_steps.step_id = s.id
            WHERE i_steps.id = ?
        """, (step_id,))
        result = cursor.fetchone()
        return AttrDict(dict(result)) if result else None

def update_instance_step_status(step_id, new_status):
    """Update the status of an instance step"""
    with DBConnection() as cursor:
        cursor.execute("""
            UPDATE instance_steps 
            SET status = ?, updated_at = datetime('now')
            WHERE id = ?
        """, (new_status, step_id))
        return cursor.rowcount > 0

# Render functions

def render_instances(checklist_id=None, status=None):
    """Render instances view with optional filtering"""
    instances = get_filtered_instances(checklist_id, status)
    
    return Div(
        # Header section with title and new button
        Div(
            H2("Instances", cls="uk-heading-medium uk-margin-remove"),
            Button("+ New Instance", 
                  cls="uk-button uk-button-primary",
                  **{
                      'uk-toggle': 'target: #new-instance-modal',
                      'type': 'button'
                  }),
            cls="uk-flex uk-flex-middle uk-flex-between uk-margin-medium-bottom"
        ),
        
        # Existing instances table
        Table(
            Thead(
                Tr(
                    Th("Checklist"),
                    Th("Instance"),
                    Th("Status"),
                    Th("Progress"),
                    Th("Created"),
                    Th("Due Date"),
                    Th("Actions")
                )
            ),
            Tbody(*(
                Tr(
                    Td(instance.checklist_title),
                    Td(instance.name),
                    Td(
                        Span(
                            instance.status,
                            cls=f"uk-label uk-label-{'success' if instance.status == 'Completed' else 'warning' if instance.status == 'Active' else 'default'}"
                        )
                    ),
                    Td(
                        Div(
                            Div(
                                style=f"width: {(instance.completed_steps/instance.total_steps)*100 if instance.total_steps else 0}%",
                                cls="uk-progress-bar"
                            ),
                            cls="uk-progress"
                        ),
                        f"{instance.completed_steps}/{instance.total_steps} steps"
                    ),
                    Td(instance.created_at[:10]),
                    Td(instance.target_date[:10] if instance.target_date else ""),
                    Td(
                        A("Continue", 
                          cls="uk-button uk-button-small uk-button-primary",
                          **{
                              'hx-get': f'/instance/{instance.id}',
                              'hx-target': '#main-content',
                              'hx-push-url': 'true'
                          })
                    )
                )
                for instance in instances
            )),
            cls="uk-table uk-table-divider uk-table-middle uk-table-hover"
        ),
        
        # Add the modal
        create_instance_modal(checklist_id) if checklist_id else "",
        
        id="main-content",
        cls="uk-container uk-margin-top"
    )


def render_instance_view(instance_id):
    instance = get_instance_with_steps(instance_id)
    if not instance:
        return Div("Instance not found", cls="uk-alert uk-alert-danger")
    
    return Div(
        # Header stays the same
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
        
        # Updated steps list with save buttons
        Div(*(
            Div(
                Div(
                    P(step.step_text, cls="uk-margin-remove uk-flex-1"),
                    Form(
                        Select(
                            Option("Not Started", selected=step.status=="Not Started"),
                            Option("In Progress", selected=step.status=="In Progress"),
                            Option("Completed", selected=step.status=="Completed"),
                            cls="uk-select uk-form-small uk-width-small uk-margin-right",
                            name="status"
                        ),
                        Button("Save",
                              cls="uk-button uk-button-small uk-button-primary",
                              type="submit"),
                        cls="uk-flex uk-flex-middle",
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

def render_instance_view_two(instance_id):
    instance = get_instance_with_steps(instance_id)
    if not instance:
        return Div("Instance not found", cls="uk-alert uk-alert-danger")
    
    return Div(
        # Header stays the same
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
        
        # Updated steps list with save buttons
        Div(*(
            Div(
                Div(
                    P(step.step_text, cls="uk-margin-remove uk-flex-1"),
                    Form(
                        Select(
                            Option("Not Started", selected=step.status=="Not Started"),
                            Option("In Progress", selected=step.status=="In Progress"),
                            Option("Completed", selected=step.status=="Completed"),
                            cls="uk-select uk-form-small uk-width-small uk-margin-right",
                            name="status"
                        ),
                        Button("Save",
                              cls="uk-button uk-button-small uk-button-primary",
                              type="submit"),
                        cls="uk-flex uk-flex-middle",
                        **{
                            'hx-put': f'/instance-step/{step.instance_step_id}/status',
                            'hx-target': f'#step-container-{step.instance_step_id}'
                        }
                    ),
                    cls="uk-flex uk-flex-middle uk-flex-between"
                ),
                cls="uk-margin-medium-bottom uk-padding-small uk-box-shadow-small",
                id=f'step-container-{step.instance_step_id}' 
            )
            for step in instance.steps
        )),
        
        id="main-content",
        cls="uk-container uk-margin-top"
    )

def render_instance_step(step):
    """Render a single instance step with consistent styling"""
    return Div(
        P(step.step_text, cls="uk-margin-remove uk-flex-1"),
        Form(
            Select(
                Option("Not Started", selected=step.status=="Not Started"),
                Option("In Progress", selected=step.status=="In Progress"),
                Option("Completed", selected=step.status=="Completed"),
                cls="uk-select uk-form-small uk-width-small uk-margin-right",
                name="status"
            ),
            Button("Save",
                  cls="uk-button uk-button-small uk-button-primary",
                  type="submit"),
            cls="uk-flex uk-flex-middle",
            **{
                'hx-put': f'/instance-step/{step.id}/status',
                'hx-target': f'#step-container-{step.id}'
            }
        ),
        cls="uk-flex uk-flex-middle uk-flex-between",
        id=f'step-container-{step.id}'
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

from fasthtml.common import *
from fasthtml.components import *
from monsterui.all import *
from datetime import datetime
from fastcore.basics import AttrDict
from db_connection import DBConnection

from models import Checklist

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
                      'hx-get': f'/checklist/{checklist.id}/instances',  # This is the changed line
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
        # Get checklist details
        cursor.execute("""
            SELECT id, title, description, description_long, created_at 
            FROM checklists WHERE id = ?
        """, (checklist_id,))
        checklist_row = cursor.fetchone()
        
        if not checklist_row:
            return None
            
        # Get steps with their references
        cursor.execute("""
            SELECT 
                s.id, s.text, s.status, s.order_index,
                sr.url as reference_url
            FROM steps s
            LEFT JOIN step_references sr ON s.id = sr.step_id
            WHERE s.checklist_id = ?
            ORDER BY s.order_index
        """, (checklist_id,))
        step_rows = cursor.fetchall()
    
    # Create the checklist using our class
    return Checklist(
        id=checklist_row['id'],
        title=checklist_row['title'],
        description=checklist_row['description'],
        description_long=checklist_row['description_long'],
        created_at=checklist_row['created_at'],
        steps=[AttrDict(dict(row)) for row in step_rows]
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
                    P(A("Reference", href=step.reference_url)) 
                    if step.reference_url 
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



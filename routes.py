#routes.py
# Standard library imports
import sqlite3
import argparse
from pathlib import Path
import logging
import os
from datetime import datetime

# FastHTML and related imports
from fasthtml.common import (
    fast_app, 
    database, 
    Path, 
    SortableJS,
    serve
)
from monsterui.all import Theme, Container

# Configuration imports
from db_connection import DB_PATH, DBConnection
from routes import *

from core_functions import *
from render_functions import * 
from main import * 


# Import necessary components at the top of the file
from fasthtml.components import Container, Div, H1, P, A, Section, Script
from monsterui.all import ContainerT, Card, DivFullySpaced, DivLAligned, UkIcon, H3, Button, ButtonT

# Import necessary components at the top of the file
from fasthtml.components import Container, Div, H1, P, A, Section, Script
from monsterui.all import ContainerT, Card, DivFullySpaced, DivLAligned, UkIcon, H3, Button, ButtonT, TextPresets

@rt('/edit/{id}')
def get(req):
    # Create sample data for testing
    # create_sample_data()
    
    # Get id from path parameters
    checklist_id = int(req.path_params['id'])
    
    # Check if checklist exists
    checklist_data = checklists(where=f"id = {checklist_id}")
    if not checklist_data:
        return Container(
            H1("Checklist Not Found"),
            P(f"No checklist with ID {checklist_id} exists."),
            A("Return Home", href="/", cls="uk-button uk-button-primary uk-margin-top")
        )
    

    checklist = checklist_data[0]

    
    # Get steps for this checklist
    checklist_steps = steps(where=f"checklist_id = {checklist_id}", order_by="order_index")
    
    # Get instances for this checklist
    checklist_instances_list = checklist_instances(where=f"checklist_id = {checklist_id}")
    
    # Add get_progress method to instances
    def get_progress(instance):
        instance_step_statuses = instance_steps(where=f"checklist_instance_id = {instance.id}")
        total = len(instance_step_statuses)
        if total == 0: return {'percentage': 0}
        completed = len([s for s in instance_step_statuses if s.status == 'Completed'])
        return {'percentage': int(completed / total * 100)}
    
    for instance in checklist_instances_list:
        instance.get_progress = lambda self=instance: get_progress(self)
    
    # Function to get references for a step
    def get_refs(step_id):
        return step_references(where=f"step_id = {step_id}")
    
    # Get reference types
    ref_types = reference_types()
    
    # Create a custom page layout
    return Container(
        # Custom navbar wrapper - simplified version
        Div(
            DivFullySpaced(
                DivLAligned(UkIcon("check-square", cls="mr-2"), H3("Checklist Manager")),
                Div(
                    A("Dashboard", href="/"),
                    A("Checklists", href="/checklists"),
                    A("Instances", href="/instances"),
                    cls="space-x-4"
                )
            ),
            cls="mb-6 p-4 border-bottom"
        ),
        
        # Page title
        Div(
            H1(f"Edit Checklist: {checklist.title}"),
            P("Make changes to your checklist", cls=TextPresets.muted_sm),
            cls="mb-6 text-center"
        ),
        
        # Just a simple card to show we got here
        Card(
            P(f"Successfully loaded checklist {checklist.id}: {checklist.title}"),
            P(f"Steps: {len(checklist_steps)}"),
            P(f"Instances: {len(checklist_instances_list)}"),
            P(f"Reference Types: {len(ref_types)}"),
            cls="p-6 mb-4"
        ),
        
        # Developer tools section
        # Card(
        #     H3("Developer Tools", cls="mb-3"),
        #     P("Use these tools for testing and debugging purposes.", cls=TextPresets.muted_sm),
        #     DivFullySpaced(
        #         Button("Reload Page", 
        #                cls=ButtonT.secondary,
        #                onclick="window.location.reload()"),
        #         Button("Reset Test Data", 
        #                cls=ButtonT.danger,
        #                hx_post="/reset-data",
        #                hx_target="reset-message")
        #     ),
        #     Div(id="reset-message", cls="mt-3"),  # Message will appear here
        #     Script("""
        #     document.addEventListener('htmx:afterRequest', function(evt) {
        #         if (evt.detail.target.id === 'reset-message') {
        #             // Wait 2 seconds then reload the page
        #             setTimeout(function() {
        #                 window.location.reload();
        #             }, 2000);
        #         }
        #     });
        #     """),
        #     cls="p-6 mb-4"
        # ),
        
        # Link back home
        Div(
            A("Return Home", href="/", cls="uk-button uk-button-primary"),
            cls="text-center"
        ),
        
        cls=(ContainerT.xl, "space-y-4")
    )

# Add a route to handle the data reset
@rt('/reset-data', methods=['POST'])
def post(req):
    # Count checklists before deletion
    checklist_count = len(checklists())
    step_count = len(steps())
    instance_count = len(checklist_instances())
    reference_count = len(step_references())
    
    # Reset the data
    clean_test_data()
    
    # Return count of deleted items
    return f"Deleted {checklist_count} checklists, {step_count} steps, {instance_count} instances, and {reference_count} references"


@rt('/db-status')
def get():
    """Route to display database status information"""
    # Create data directory if it doesn't exist
    data_dir = Path('data')
    data_dir.mkdir(exist_ok=True)
    
    results = []
    results.append(f"Database path: {DB_PATH}")
    
    # Check if database file exists
    if DB_PATH.exists():
        results.append(f"Database file exists: {DB_PATH.stat().st_size} bytes")
    else:
        results.append(f"Database file does not exist!")
    
    # Check tables and data using your DBConnection
    try:
        with DBConnection() as cursor:
            # List all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            table_names = [t[0] for t in tables]
            results.append(f"Tables in database: {table_names}")
            
            # Check data in each table
            for table in table_names:
                if table.startswith('sqlite_'):
                    continue  # Skip SQLite internal tables
                    
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                results.append(f"Table '{table}': {count} rows")
                
                # Show sample data if available
                if count > 0:
                    cursor.execute(f"SELECT * FROM {table} LIMIT 1")
                    sample = dict(cursor.fetchone())
                    results.append(f"Sample data: {sample}")
        
        # Check tables from fast_app connection
        results.append("\nData from fast_app tables:")
        results.append(f"Checklists: {len(checklists())} rows")
        results.append(f"Steps: {len(steps())} rows")
        results.append(f"Reference types: {len(reference_types())} rows")
        results.append(f"Step references: {len(step_references())} rows")
        results.append(f"Checklist instances: {len(checklist_instances())} rows")
        results.append(f"Instance steps: {len(instance_steps())} rows")
        
    except Exception as e:
        results.append(f"Error accessing database: {str(e)}")
    
    # Return results as HTML
    return Div(
        H2("Database Status"),
        *[P(line) for line in results],
        cls="uk-container uk-padding"
    )


@rt('/checklists-data')
def get():
    """Display all data from the checklists table """
    try:
        # Get all checklists
        all_checklists = checklists()
        
        # Create a section for each checklist
        checklist_sections = []
        for cl in all_checklists:
            # Create a card for each checklist with its details
            checklist_card = Card(
                H3(f"Checklist #{cl.id}: {cl.title}"),
                P(f"Description: {cl.description}"),
                P(f"Long Description: {cl.description_long or 'None'}"),
                P(f"Created: {cl.created_at}"),
                P(f"Last Modified: {cl.last_modified}"),
                P(f"Modified By: {cl.last_modified_by}"),
                # Get steps for this checklist
                H4("Steps:"),
                Ul(*[Li(f"#{s.id}: {s.text} (Order: {s.order_index})") 
                     for s in steps() if s.checklist_id == cl.id]),
                cls="uk-card-default uk-padding uk-margin"
            )
            checklist_sections.append(checklist_card)
        
        # If no checklists found
        if not checklist_sections:
            checklist_sections = [P("No checklists found in the database.")]
        
        # Return the complete page
        return Div(
            H2("All Checklists Data"),
            P(f"Total checklists: {len(all_checklists)}"),
            *checklist_sections,
            cls="uk-container uk-padding"
        )
    except Exception as e:
        # Handle any errors
        return Div(
            H2("Error Accessing Checklists Data"),
            P(f"An error occurred: {str(e)}"),
            cls="uk-container uk-padding"
        )


@rt('/data-control')
def get():
    """Data control panel with create/delete buttons and data display"""
    try:
        # Create action buttons
        control_panel = Div(
            H2("Data Control Panel"),
            Div(
                Button(
                    "Create Sample Data",
                    hx_post="/data-control/create",
                    hx_target="#data-display",
                    hx_swap="outerHTML",
                    cls="uk-button uk-button-primary uk-margin-right"
                ),
                Button(
                    "Delete All Data",
                    hx_post="/data-control/delete",
                    hx_target="#data-display",
                    hx_swap="outerHTML",
                    hx_confirm="Are you sure you want to delete all data?",
                    cls="uk-button uk-button-danger"
                ),
                cls="uk-margin-medium-bottom"
            ),
            cls="uk-container uk-padding uk-padding-remove-bottom"
        )
        
        # Data display section
        data_display = render_data_display()
        
        return Div(
            control_panel,
            data_display,
            cls="uk-width-1-1"
        )
    except Exception as e:
        return Div(
            H2("Error"),
            P(f"An error occurred: {str(e)}"),
            cls="uk-container uk-padding"
        )

@rt('/data-control/create', methods=['POST'])
def post():
    """Create sample data and return updated display"""
    try:
        result = create_sample_data()
        return render_data_display(message=f"Sample data created successfully: {len(result)} checklists")
    except Exception as e:
        return render_data_display(error=f"Error creating data: {str(e)}")




@rt('/data-control/delete', methods=['POST'])
def post():
    """Delete all data using MiniDataAPI methods"""
    try:
        # Get all records from each table
        instance_step_records = instance_steps()
        reference_records = step_references()
        instance_records = checklist_instances()
        step_records = steps()
        checklist_records = checklists()
        ref_type_records = reference_types()
        
        # Delete records in correct order to respect foreign keys
        for record in instance_step_records: instance_steps.delete(record.id)
        for record in reference_records: step_references.delete(record.id)
        for record in instance_records: checklist_instances.delete(record.id)
        for record in step_records: steps.delete(record.id)
        for record in checklist_records: checklists.delete(record.id)
        for record in ref_type_records: reference_types.delete(record.id)
        
        # Return the updated display
        return render_data_display(message="All data deleted successfully")
    except Exception as e:
        return render_data_display(error=f"Error deleting data: {str(e)}")




# @rt('/data-control/delete', methods=['POST'])
# def post():
#     """Delete all data and return updated display with debug info"""
#     debug_messages = []
    
#     try:
#         # First try the original clean_test_data function
#         debug_messages.append("Attempting clean_test_data()...")
#         try:
#             result = clean_test_data()
#             debug_messages.append(f"clean_test_data() completed: {result}")
#         except Exception as e:
#             debug_messages.append(f"Error in clean_test_data(): {str(e)}")
        
#         # Check counts before direct deletion
#         debug_messages.append(f"Before direct deletion - Counts: Checklists={len(checklists())}, Steps={len(steps())}, References={len(step_references())}")
        
#         # Try direct deletion from fast_app tables
#         debug_messages.append("Attempting direct table deletion...")
        
#         # Delete instance_steps
#         try:
#             count = len(instance_steps())
#             instance_steps.delete_all()
#             debug_messages.append(f"Deleted {count} instance steps, remaining: {len(instance_steps())}")
#         except Exception as e:
#             debug_messages.append(f"Error deleting instance_steps: {str(e)}")
        
#         # Delete step_references
#         try:
#             count = len(step_references())
#             step_references.delete_all()
#             debug_messages.append(f"Deleted {count} references, remaining: {len(step_references())}")
#         except Exception as e:
#             debug_messages.append(f"Error deleting step_references: {str(e)}")
        
#         # Delete checklist_instances
#         try:
#             count = len(checklist_instances())
#             checklist_instances.delete_all()
#             debug_messages.append(f"Deleted {count} instances, remaining: {len(checklist_instances())}")
#         except Exception as e:
#             debug_messages.append(f"Error deleting checklist_instances: {str(e)}")
        
#         # Delete steps
#         try:
#             count = len(steps())
#             steps.delete_all()
#             debug_messages.append(f"Deleted {count} steps, remaining: {len(steps())}")
#         except Exception as e:
#             debug_messages.append(f"Error deleting steps: {str(e)}")
        
#         # Delete checklists
#         try:
#             count = len(checklists())
#             checklists.delete_all()
#             debug_messages.append(f"Deleted {count} checklists, remaining: {len(checklists())}")
#         except Exception as e:
#             debug_messages.append(f"Error deleting checklists: {str(e)}")
        
#         # Delete reference_types if needed
#         try:
#             count = len(reference_types())
#             reference_types.delete_all()
#             debug_messages.append(f"Deleted {count} reference types, remaining: {len(reference_types())}")
#         except Exception as e:
#             debug_messages.append(f"Error deleting reference_types: {str(e)}")
        
#         # Try alternate deletion method with direct SQL
#         try:
#             debug_messages.append("Attempting direct SQL deletion...")
#             # Get database connection from one of the tables
#             db = checklists.db
            
#             # Execute direct SQL deletion in correct order
#             db.execute("DELETE FROM instance_steps")
#             db.execute("DELETE FROM step_references")
#             db.execute("DELETE FROM checklist_instances")
#             db.execute("DELETE FROM steps")
#             db.execute("DELETE FROM checklists")
#             db.execute("DELETE FROM reference_types")
#             debug_messages.append("Direct SQL deletion completed")
#         except Exception as e:
#             debug_messages.append(f"Error with direct SQL deletion: {str(e)}")
        
#         # Final check
#         final_counts = f"Final counts: Checklists={len(checklists())}, Steps={len(steps())}, References={len(step_references())}"
#         debug_messages.append(final_counts)
        
#         # Return the updated display with debug info
#         return render_data_display(
#             message="Data deletion attempted. See debug information below.",
#             debug_info=debug_messages
#         )
#     except Exception as e:
#         debug_messages.append(f"Unexpected error: {str(e)}")
#         return render_data_display(
#             error=f"Error deleting data: {str(e)}",
#             debug_info=debug_messages
#         )




def render_data_display(message=None, error=None, debug_info=None):
    """Render the data display section showing all tables"""
    # Get counts
    cl_count = len(checklists())
    step_count = len(steps())
    ref_count = len(step_references())
    instance_count = len(checklist_instances())
    
    # Status message
    status = ""
    if message:
        status = Div(P(message, cls="uk-text-success"), cls="uk-alert uk-alert-success")
    elif error:
        status = Div(P(error, cls="uk-text-danger"), cls="uk-alert uk-alert-danger")
    
    # Debug information
    debug_section = ""
    if debug_info:
        debug_section = Div(
            H4("Debug Information"),
            Ul(*[Li(msg) for msg in debug_info]),
            cls="uk-alert uk-alert-warning"
        )
    
    # Build tabs for different data types
    tabs = Div(
        Ul(
            Li(A("Checklists", href="#checklists-tab"), cls="uk-active"),
            Li(A("Steps", href="#steps-tab")),
            Li(A("References", href="#references-tab")),
            Li(A("Instances", href="#instances-tab")),
            cls="uk-tab"
        ),
        Ul(
            # Checklists tab
            Li(
                render_checklists_table(),
                id="checklists-tab",
                cls="uk-active"
            ),
            # Steps tab
            Li(
                render_steps_table(),
                id="steps-tab"
            ),
            # References tab
            Li(
                render_references_table(),
                id="references-tab"
            ),
            # Instances tab
            Li(
                render_instances_table(),
                id="instances-tab"
            ),
            cls="uk-switcher uk-margin"
        ),
        cls="uk-margin-medium-top"
    )
    
    return Div(
        H3("Database Contents"),
        P(f"Checklists: {cl_count} | Steps: {step_count} | References: {ref_count} | Instances: {instance_count}"),
        status,
        debug_section,
        tabs,
        id="data-display",
        cls="uk-container uk-padding uk-padding-remove-top"
    )


def render_checklists_table():
    """Render a table of all checklists"""
    all_checklists = checklists()
    
    if not all_checklists:
        return P("No checklists found.")
        
    rows = []
    for cl in all_checklists:
        rows.append(Tr(
            Td(cl.id),
            Td(cl.title),
            Td(cl.description),
            Td(A(f"Edit", href=f"/edit/{cl.id}")),
            Td(f"{len([s for s in steps() if s.checklist_id == cl.id])} steps")
        ))
    
    return Table(
        Thead(
            Tr(
                Th("ID"),
                Th("Title"),
                Th("Description"),
                Th("Actions"),
                Th("Steps")
            )
        ),
        Tbody(*rows),
        cls="uk-table uk-table-striped uk-table-hover"
    )

def render_steps_table():
    """Render a table of all steps"""
    all_steps = steps()
    
    if not all_steps:
        return P("No steps found.")
        
    rows = []
    for step in all_steps:
        cl = next((c for c in checklists() if c.id == step.checklist_id), None)
        cl_title = cl.title if cl else "Unknown"
        
        rows.append(Tr(
            Td(step.id),
            Td(step.checklist_id),
            Td(cl_title),
            Td(step.text),
            Td(step.order_index),
            Td(f"{len([r for r in step_references() if r.step_id == step.id])} refs")
        ))
    
    return Table(
        Thead(
            Tr(
                Th("ID"),
                Th("Checklist ID"),
                Th("Checklist"),
                Th("Text"),
                Th("Order"),
                Th("References")
            )
        ),
        Tbody(*rows),
        cls="uk-table uk-table-striped uk-table-hover"
    )

def render_references_table():
    """Render a table of all references"""
    all_refs = step_references()
    
    if not all_refs:
        return P("No references found.")
        
    rows = []
    for ref in all_refs:
        step = next((s for s in steps() if s.id == ref.step_id), None)
        step_text = step.text[:30] + "..." if step and len(step.text) > 30 else (step.text if step else "Unknown")
        
        rows.append(Tr(
            Td(ref.id),
            Td(ref.step_id),
            Td(step_text),
            Td(ref.url[:50] + "..." if len(ref.url) > 50 else ref.url),
            Td(ref.reference_type_id)
        ))
    
    return Table(
        Thead(
            Tr(
                Th("ID"),
                Th("Step ID"),
                Th("Step"),
                Th("URL/Text"),
                Th("Type")
            )
        ),
        Tbody(*rows),
        cls="uk-table uk-table-striped uk-table-hover"
    )

def render_instances_table():
    """Render a table of all instances"""
    all_instances = checklist_instances()
    
    if not all_instances:
        return P("No instances found.")
        
    rows = []
    for inst in all_instances:
        cl = next((c for c in checklists() if c.id == inst.checklist_id), None)
        cl_title = cl.title if cl else "Unknown"
        
        rows.append(Tr(
            Td(inst.id),
            Td(inst.checklist_id),
            Td(cl_title),
            Td(inst.name),
            Td(inst.status),
            Td(inst.target_date or "None")
        ))
    
    return Table(
        Thead(
            Tr(
                Th("ID"),
                Th("Checklist ID"),
                Th("Checklist"),
                Th("Name"),
                Th("Status"),
                Th("Target Date")
            )
        ),
        Tbody(*rows),
        cls="uk-table uk-table-striped uk-table-hover"
    )


@rt('/db-persistence-check')
def get():
    """Check database persistence and configuration"""
    results = []
    
    # 1. Check database path and file
    results.append(f"Database path: {DB_PATH}")
    if DB_PATH.exists():
        file_size = DB_PATH.stat().st_size
        results.append(f"Database file exists: {file_size} bytes")
        if file_size < 5000:
            results.append("Warning: Database file is very small, might be empty or reset")
    else:
        results.append("Database file does not exist! Will be created on first use.")
    
    # 2. Check if the database is in-memory
    try:
        # Get connection string from fast_app tables
        db_conn = checklists.db.conn
        pragmas = {}
        
        # Get important SQLite pragmas
        cursor = db_conn.execute("PRAGMA journal_mode;")
        pragmas['journal_mode'] = cursor.fetchone()[0]
        
        cursor = db_conn.execute("PRAGMA synchronous;")
        pragmas['synchronous'] = cursor.fetchone()[0]
        
        cursor = db_conn.execute("PRAGMA temp_store;")
        pragmas['temp_store'] = cursor.fetchone()[0]
        
        # Check if using memory database
        if ':memory:' in str(db_conn) or 'mode=memory' in str(db_conn):
            results.append("CRITICAL: Using in-memory database! Data will not persist between restarts.")
        
        results.append(f"SQLite pragmas: {pragmas}")
        
        # Check if fast_app is using the same file as DB_PATH
        fast_app_db_path = str(db_conn).split("'")[1] if "'" in str(db_conn) else "unknown"
        results.append(f"fast_app database path: {fast_app_db_path}")
        if fast_app_db_path != str(DB_PATH) and fast_app_db_path != "unknown":
            results.append(f"WARNING: fast_app database path ({fast_app_db_path}) differs from DB_PATH ({DB_PATH})")
    except Exception as e:
        results.append(f"Error checking database connection: {str(e)}")
    
    # 3. Test data creation and persistence
    try:
        # Create a test checklist
        test_checklist = checklists.insert({
            'title': 'Persistence Test',
            'description': 'Testing database persistence',
            'description_long': f'Created at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
        })
        results.append(f"Created test checklist with ID {test_checklist.id}")
        
        # Force commit to database
        checklists.db.conn.commit()
        results.append("Forced database commit")
        
        # Check if file size changed
        if DB_PATH.exists():
            new_size = DB_PATH.stat().st_size
            results.append(f"Database file size after insert: {new_size} bytes")
    except Exception as e:
        
        results.append(f"Error creating test data: {str(e)}")
    
    # 4. Suggest fixes
    results.append("\nPossible Solutions:")
    results.append("1. Ensure DB_PATH is set to an absolute path, not a relative one")
    results.append("2. Make sure the 'data' directory exists and is writable")
    results.append("3. Check if fast_app is configured to use the same database file")
    results.append("4. Add explicit commits after data operations")
    
    # Return results as HTML
    return Div(
        H2("Database Persistence Diagnostic"),
        *[P(line) for line in results],
        cls="uk-container uk-padding"
    )

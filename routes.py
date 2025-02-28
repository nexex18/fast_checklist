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
from monsterui.all import Theme

# Configuration imports
from config import DB_PATH
from db_connection import DBConnection
from routes import *

from core_functions import *
from render_functions import * 
from main import * 


@rt('/')
def get(req):
    try:
        # Create or get sample data
        data = create_sample_data()
        
        # Get a sample checklist
        checklist = checklists()[0]
        
        # Get steps for the checklist
        checklist_steps = [s for s in steps() if s.checklist_id == checklist.id]
        
        # Get instances for the checklist
        checklist_instances_list = [i for i in checklist_instances() if i.checklist_id == checklist.id][:2]
        
        # Add get_progress method to instances for testing
        def get_progress(self):
            if self.status == 'Not Started':
                return {'percentage': 0}
            elif self.status == 'In Progress':
                return {'percentage': 50}
            else:
                return {'percentage': 100}
        
        for instance in checklist_instances_list:
            instance.get_progress = lambda self=instance: get_progress(self)
        
        # Function to get references for a step
        def get_refs(step_id):
            return [ref for ref in step_references() if ref.step_id == step_id]
        
        # Get reference types
        ref_types = reference_types()

        # LAZY IMPORT of render function
        from render_functions import render_checklist_edit_page
        
        # Use the render function to create the complete page
        return render_checklist_edit_page(checklist, checklist_steps, checklist_instances_list, ref_types, get_refs)
    
    except Exception as e:
        LOGGER.error(f"Error in home page route: {e}")
        # Consider returning an error page or a generic error response
        raise
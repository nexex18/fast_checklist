import os
from fasthtml.common import *
from fasthtml.common import RedirectResponse as redirect
from monsterui.all import *
from datetime import datetime
import argparse

from fastcore.basics import AttrDict, patch

# Import from your local modules
from config import DB_PATH
from models import Checklist
from checklist_list import (checklist_row, create_checklist_modal, get_checklist_with_steps, 
                          render_steps, render_checklist_page, checklist_table, render_main_page)
from instance_functions import (get_instance_with_steps, get_filtered_instances, create_instance_modal,
                              create_new_instance, get_instance_step, update_instance_step_status,
                              render_instances, render_instance_view, render_instance_step)


from checklist_edit import (render_checklist_edit, render_new_step_modal, render_checklist_header,
                          render_checklist_details, render_checklist_title_section, render_sortable_steps,
                          render_step_item, update_steps_order, db_update_step,
                          get_step, render_step_text, render_step_reference, get_step_reference, update_step_reference, validate_url)


from db_connection import DBConnection
from routes import *

# CLI Arguments
parser = argparse.ArgumentParser()
parser.add_argument('-refresh', action='store_true', help='Refresh the database on startup')
args = parser.parse_args()

# Database Setup
os.makedirs('data', exist_ok=True)

if args.refresh and DB_PATH.exists():
    print("Refreshing database...")
    DB_PATH.unlink()
    for ext in ['-wal', '-shm']:
        path = DB_PATH.parent / f"{DB_PATH.name}{ext}"
        if path.exists(): path.unlink()


table_config = {
    'checklists': {
        'id': int,
        'title': str,
        'description': str,
        'description_long': str,
        'created_at': str,
        'pk': 'id'
    },
    'steps': {
        'id': int,
        'checklist_id': int,
        'text': str,
        'status': str,
        'order_index': int,
        'pk': 'id'
    }
}


app, rt, checklists, steps = fast_app(  
    str(DB_PATH),
    checklists=table_config['checklists'],
    steps=table_config['steps'],  
    hdrs=(SortableJS('.sortable'), Theme.blue.headers()), 
    live=True
)


if __name__ == '__main__':
    serve()

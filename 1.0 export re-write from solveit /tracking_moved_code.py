


DB_PATH = Path('data/checklists.db')

class DBConnection:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        
    def __enter__(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        return self.conn.cursor()
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.commit()
        self.conn.close()

def create_triggers():
    with DBConnection() as cur:
        # Drop existing triggers first
        triggers = ['steps', 'checklists', 'checklist_instances', 'instance_steps', 'reference_types', 'step_references']
        for t in triggers:
            cur.execute(f"DROP TRIGGER IF EXISTS update_{t}_last_modified")
        
        # Steps table trigger
        cur.execute("""
            CREATE TRIGGER update_steps_last_modified 
            AFTER UPDATE ON steps
            BEGIN
                UPDATE steps 
                SET last_modified = CURRENT_TIMESTAMP
                WHERE id = NEW.id 
                AND (OLD.text != NEW.text 
                     OR OLD.checklist_id != NEW.checklist_id 
                     OR OLD.order_index != NEW.order_index);
            END;
        """)
        
        # Checklists trigger
        cur.execute("""
            CREATE TRIGGER update_checklists_last_modified 
            AFTER UPDATE ON checklists
            BEGIN
                UPDATE checklists 
                SET last_modified = CURRENT_TIMESTAMP
                WHERE id = NEW.id 
                AND (OLD.title != NEW.title 
                     OR OLD.description != NEW.description 
                     OR OLD.description_long != NEW.description_long);
            END;
        """)
        
        # Checklist instances trigger
        cur.execute("""
            CREATE TRIGGER update_checklist_instances_last_modified 
            AFTER UPDATE ON checklist_instances
            BEGIN
                UPDATE checklist_instances 
                SET last_modified = CURRENT_TIMESTAMP
                WHERE id = NEW.id 
                AND (OLD.name != NEW.name 
                     OR OLD.description != NEW.description 
                     OR OLD.status != NEW.status 
                     OR OLD.target_date != NEW.target_date);
            END;
        """)
        
        # Instance steps trigger (rewritten to match pattern)
        cur.execute("""
            CREATE TRIGGER update_instance_steps_last_modified 
            AFTER UPDATE ON instance_steps
            BEGIN
                UPDATE instance_steps 
                SET last_modified = CURRENT_TIMESTAMP
                WHERE id = NEW.id 
                AND (OLD.status != NEW.status 
                     OR COALESCE(OLD.notes, '') IS NOT COALESCE(NEW.notes, '')
                     OR OLD.checklist_instance_id != NEW.checklist_instance_id 
                     OR OLD.step_id != NEW.step_id);
            END;
        """)
        
        # Reference types trigger
        cur.execute("""
            CREATE TRIGGER update_reference_types_last_modified 
            AFTER UPDATE ON reference_types
            BEGIN
                UPDATE reference_types 
                SET last_modified = CURRENT_TIMESTAMP
                WHERE id = NEW.id 
                AND (OLD.name != NEW.name 
                     OR OLD.description != NEW.description);
            END;
        """)
        
        # Step references trigger
        cur.execute("""
            CREATE TRIGGER update_step_references_last_modified 
            AFTER UPDATE ON step_references
            BEGIN
                UPDATE step_references 
                SET last_modified = CURRENT_TIMESTAMP
                WHERE id = NEW.id 
                AND (OLD.url != NEW.url 
                     OR OLD.reference_type_id != NEW.reference_type_id);
            END;
        """)

import os
from fasthtml.common import *
from fasthtml.common import RedirectResponse as redirect
from monsterui.all import *
from datetime import datetime
import argparse

from fastcore.basics import AttrDict, patch


# CLI Arguments
parser = argparse.ArgumentParser()
parser.add_argument('-refresh', action='store_true', help='Refresh the database on startup')
args = parser.parse_args()

# Database Setup
os.makedirs('data', exist_ok=True)

def clean_db():
    if DB_PATH.exists():
        print("Cleaning database...")
        if 'db' in locals():
            db.close()
        DB_PATH.unlink()
        for ext in ['-wal', '-shm']:
            path = DB_PATH.parent / f"{DB_PATH.name}{ext}"
            if path.exists(): path.unlink()

# Always clean for now while we debug
clean_db()

if args.refresh and DB_PATH.exists():
    print("Refreshing database...")
    # Close any existing connections first
    if 'db' in locals():
        db.close()
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
        'last_modified': str,
        'last_modified_by': str,
        'pk': 'id',
        'defaults': {
            'created_at': 'CURRENT_TIMESTAMP',
            'last_modified': 'CURRENT_TIMESTAMP',
            'last_modified_by': 'admin'
        }
    }
    ,
    'steps': {
        'id': int,
        'checklist_id': int,
        'text': str,
        'order_index': int,
        'created_at': str,
        'last_modified': str,
        'last_modified_by': str,
        'pk': 'id',
        'foreign_keys': {'checklist_id': 'checklists.id'},
        'defaults': {
            'created_at': 'CURRENT_TIMESTAMP',
            'last_modified': 'CURRENT_TIMESTAMP',
            'last_modified_by': 'admin'
        }
    },
    'checklist_instances': {
        'id': int,
        'checklist_id': int,
        'name': str,
        'description': str,
        'status': str,
        'created_at': str,
        'last_modified': str,
        'last_modified_by': str,
        'target_date': str,
        'pk': 'id',
        'foreign_keys': {'checklist_id': 'checklists.id'},
        'defaults': {
            'status': 'Not Started',
            'created_at': 'CURRENT_TIMESTAMP',
            'last_modified': 'CURRENT_TIMESTAMP',
            'last_modified_by': 'admin'
        }
    },
    'instance_steps': {
        'id': int,
        'checklist_instance_id': int,
        'step_id': int,
        'status': str,
        'notes': str,
        'created_at': str,
        'last_modified': str,
        'last_modified_by': str,
        'pk': 'id',
        'foreign_keys': {
            'checklist_instance_id': 'checklist_instances.id',
            'step_id': 'steps.id'
        },
        'defaults': {
            'status': 'Not Started',
            'created_at': 'CURRENT_TIMESTAMP',
            'last_modified': 'CURRENT_TIMESTAMP',
            'last_modified_by': 'admin'
        }
    },
    'reference_types': {
        'id': int,
        'name': str,
        'description': str,
        'created_at': str,
        'last_modified': str,
        'last_modified_by': str,
        'pk': 'id',
        'defaults': {
            'created_at': 'CURRENT_TIMESTAMP',
            'last_modified': 'CURRENT_TIMESTAMP',
            'last_modified_by': 'admin'
        }
    },
    'step_references': {
        'id': int,
        'step_id': int,
        'url': str,
        'reference_type_id': int,
        'created_at': str,
        'last_modified': str,
        'last_modified_by': str,
        'pk': 'id',
        'foreign_keys': {
            'step_id': 'steps.id',
            'reference_type_id': 'reference_types.id'
        },
        'defaults': {
            'reference_type_id': 1,
            'created_at': 'CURRENT_TIMESTAMP',
            'last_modified': 'CURRENT_TIMESTAMP',
            'last_modified_by': 'admin'
        }
    }
}

app, rt, (checklists, _), (steps, _), (checklist_instances, _), (instance_steps, _), (reference_types, _), (step_references, _) = fast_app(
    str(DB_PATH),
    hdrs=(SortableJS('.sortable'), Theme.blue.headers()),
    live=True,
    **table_config
)

Step = steps.dataclass()
Checklist = checklists.dataclass()
StepReference = step_references.dataclass()

create_triggers()

def add_reference_type(name, description):
    name = name.upper()
    if len(reference_types(where=f"name COLLATE BINARY = '{name}'")) > 0:
        return False 
    else:
        reference_types.insert(name=name, description=description)
        return True

add_reference_type(name='URL', description='URL')
add_reference_type(name='API', description='API endpoint')


# I've moved the above code 


def _validate_checklist_exists(checklist_id):
    """Validate checklist exists and return it, or raise ValueError"""
    if not isinstance(checklist_id, int) or checklist_id < 1:
        raise ValueError(f"Invalid checklist_id: {checklist_id}")
    result = checklists(where=f"id = {checklist_id}")
    if not result:
        raise ValueError(f"Checklist not found: {checklist_id}")
    return result[0]

def _validate_step_exists(step_id):
    """Validate step exists and return it, or raise ValueError"""
    if not isinstance(step_id, int) or step_id < 1:
        raise ValueError(f"Invalid step_id: {step_id}")
    result = steps(where=f"id = {step_id}")
    if not result:
        raise ValueError(f"Step not found: {step_id}")
    return result[0]

def _get_reference_type_id(type_name):
    """Get reference type ID, creating if needed. Return ID."""
    type_name = type_name.upper()
    result = reference_types(where=f"name = '{type_name}'")
    if result:
        return result[0].id
    # Create new type if doesn't exist
    return reference_types.insert(
        name=type_name,
        description=f"Auto-created reference type: {type_name}"
    ).id


def test_validation_functions():
    # Test checklist validation
    test_checklist = checklists.insert(
        title="Test Checklist",
        description="Test Description"
    )
    
    try:
        # Should work
        assert _validate_checklist_exists(test_checklist.id)
        
        # Should fail
        try:
            _validate_checklist_exists(-1)
            assert False, "Should have failed with negative ID"
        except ValueError:
            pass
            
        try:
            _validate_checklist_exists(999999)
            assert False, "Should have failed with non-existent ID"
        except ValueError:
            pass
    
        # Test step validation
        test_step = steps.insert(
            checklist_id=test_checklist.id,
            text="Test Step",
            order_index=1
        )
        
        # Should work
        assert _validate_step_exists(test_step.id)
        
        # Should fail
        try:
            _validate_step_exists(-1)
            assert False, "Should have failed with negative ID"
        except ValueError:
            pass
            
        # Test reference type
        type_id1 = _get_reference_type_id("TEST_TYPE")
        type_id2 = _get_reference_type_id("TEST_TYPE")
        assert type_id1 == type_id2, "Should return same ID for same type"
        
        print("All validation tests passed!")
        
    finally:
        # Cleanup
        if 'test_step' in locals():
            steps.delete(test_step.id)
        if 'test_checklist' in locals():
            checklists.delete(test_checklist.id)

# Run the tests
test_validation_functions()

# I've moved the above code 


def create_checklist(title, description, description_long=None):
    """Create a new checklist
    Args:
        title: str - Title of the checklist
        description: str - Short description
        description_long: str, optional - Detailed description
    Returns:
        Checklist object for chaining
    """
    if not title or not description:
        raise ValueError("Title and description are required")
    
    return checklists.insert(
        title=title,
        description=description,
        description_long=description_long
    )



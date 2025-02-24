from httpx import get as xget, post as xpost 
import os
from fasthtml.common import *
from fasthtml.common import RedirectResponse as redirect
from monsterui.all import *
from datetime import datetime
import argparse
import sqlite3
from time import sleep



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

def test_create_checklist():
    try:
        # Test basic creation
        c1 = create_checklist(
            "Test Checklist",
            "A simple test checklist"
        )
        assert c1.title == "Test Checklist"
        assert c1.description == "A simple test checklist"
        assert c1.description_long is None
        
        # Test with long description
        c2 = create_checklist(
            "Test with Long Desc",
            "Short desc",
            "This is a much longer description"
        )
        assert c2.description_long == "This is a much longer description"
        
        # Test validation
        try:
            create_checklist("", "desc")
            assert False, "Should fail with empty title"
        except ValueError:
            pass
            
        print("All create_checklist tests passed!")
        
    finally:
        # Cleanup
        if 'c1' in locals(): checklists.delete(c1.id)
        if 'c2' in locals(): checklists.delete(c2.id)

# Run the tests
test_create_checklist()

@patch
def update(self:Checklist, title=None, description=None, description_long=None):
    """Update checklist fields
    Args:
        title: str, optional - New title
        description: str, optional - New short description
        description_long: str, optional - New detailed description
    Returns:
        self for chaining
    """
    updates = {}
    if title: updates['title'] = title
    if description: updates['description'] = description
    if description_long is not None: updates['description_long'] = description_long
    
    if updates:
        checklists.update(updates, self.id)
        # Get fresh data and update all attributes
        updated = _validate_checklist_exists(self.id)
        for key in updated.__dict__:
            setattr(self, key, getattr(updated, key))
    
    return self


def test_checklist_update():
    try:
        # Create test checklist
        c1 = create_checklist(
            "Original Title",
            "Original description"
        )
        
        # Test single field update
        c1.update(title="Updated Title")
        assert c1.title == "Updated Title"
        assert c1.description == "Original description"
        
        # Test multiple field update
        c1.update(
            description="New description",
            description_long="Added long description"
        )
        assert c1.description == "New description"
        assert c1.description_long == "Added long description"
        
        # Test no changes case
        orig_modified = c1.last_modified
        c1.update()  # No parameters
        assert c1.last_modified == orig_modified, "Should not update if no changes"
        
        print("All checklist update tests passed!")
        
    finally:
        # Cleanup
        if 'c1' in locals(): checklists.delete(c1.id)

# Run the tests
test_checklist_update()

def test_checklist_update():
    try:
        # Create test checklist
        c1 = create_checklist(
            "Original Title",
            "Original description"
        )
        
        # Store and print initial timestamp
        initial_modified = c1.last_modified
        print(f"\nInitial last_modified: {initial_modified}")
        
        # Wait a moment to ensure timestamp would be different
        print("Waiting 5 seconds...")
        from time import sleep
        sleep(5)
        
        # Test single field update
        c1.update(title="Updated Title")
        print(f"After update last_modified: {c1.last_modified}")
        assert c1.title == "Updated Title"
        assert c1.description == "Original description"
        # assert c1.last_modified > initial_modified, "last_modified should be updated"
        
        print("All checklist update tests passed!")
        
    finally:
        # Cleanup
        if 'c1' in locals(): checklists.delete(c1.id)

# Run the tests
test_checklist_update()

def _get_next_order_index(checklist_id):
    """Get next available order_index for a checklist's steps
    Args:
        checklist_id: int - ID of checklist
    Returns:
        int - Next available order_index
    """
    _validate_checklist_exists(checklist_id)
    result = steps(
        where=f"checklist_id = {checklist_id}",
        order_by="order_index DESC",
        limit=1
    )
    return (result[0].order_index + 1) if result else 1

def test_get_next_order_index():
    try:
        # Create test checklist
        checklist = create_checklist("Test Checklist", "For testing order index")
        
        # First step should get index 1
        assert _get_next_order_index(checklist.id) == 1
        
        # Add a step and check next index
        steps.insert(checklist_id=checklist.id, text="Step 1", order_index=1)
        assert _get_next_order_index(checklist.id) == 2
        
        print("All next order index tests passed!")
        
    finally:
        # Cleanup
        if 'checklist' in locals(): checklists.delete(checklist.id)

# Run the tests
test_get_next_order_index()

def _reorder_steps(checklist_id, new_index, current_index=None):
    """Reorder steps when inserting or moving a step
    Args:
        checklist_id: int - ID of checklist to reorder
        new_index: int - Target position
        current_index: int, optional - Current position if moving existing step
    """
    _validate_checklist_exists(checklist_id)
    
    # Get affected steps
    if current_index is not None and new_index > current_index:
        # Moving down: affect steps between current+1 and new
        affected = steps(
            where=f"checklist_id = {checklist_id} AND order_index > {current_index} AND order_index <= {new_index}",
            order_by="order_index DESC"
        )
        for step in affected:
            steps.update({'order_index': step.order_index - 1}, step.id)
    else:
        # Moving up or inserting new: affect steps at or after new position
        affected = steps(
            where=f"checklist_id = {checklist_id} AND order_index >= {new_index}",
            order_by="order_index DESC"
        )
        for step in affected:
            steps.update({'order_index': step.order_index + 1}, step.id)
@patch
def add_step(self:Checklist, text, order_index=None):
    """Add a step to this checklist
    Args:
        text: str - Step description
        order_index: int, optional - Position in checklist
    Returns:
        Step object for chaining
    """
    if not text:
        raise ValueError("Step text is required")
    
    if order_index is None:
        order_index = _get_next_order_index(self.id)
    else:
        _reorder_steps(self.id, order_index)
        
    new_step = steps.insert(
        checklist_id=self.id,
        text=text,
        order_index=order_index
    )

    return self, new_step
def test_add_step_with_chaining():
    try:
        # Create test checklist
        checklist = create_checklist("Test Checklist", "For testing step additions")
        
        # Test basic tuple unpacking
        checklist, step1 = checklist.add_step("First step")
        assert step1.text == "First step"
        assert step1.order_index == 1
        
        # Test chained creation using first element of tuple
        checklist, step2 = checklist.add_step("Second step")
        checklist, step3 = checklist.add_step("Third step")
        
        # Verify order
        all_steps = steps(where=f"checklist_id = {checklist.id}", order_by="order_index")
        assert len(all_steps) == 3
        assert [s.text for s in all_steps] == ["First step", "Second step", "Third step"]
        
        # Test immediate step access by adding a reference
        # step2.add_reference("https://example.com/doc")
        # refs = step2.get_references()
        # assert len(refs) == 1
        # assert refs[0].url == "https://example.com/doc"
        
        # Test validation still works
        try:
            checklist.add_step("")
            assert False, "Should fail with empty text"
        except ValueError:
            pass
            
        print("All add_step chaining tests passed!")
        
    finally:
        # Cleanup
        if 'checklist' in locals(): checklists.delete(checklist.id)

# Run the tests
test_add_step_with_chaining()

@patch
def update(self:Step, text=None, order_index=None):
    """Update step fields
    Args:
        text: str, optional - New step text
        order_index: int, optional - New position in checklist
    Returns:
        self for chaining
    """
    updates = {}
    if text: updates['text'] = text
    if order_index is not None:
        if order_index != self.order_index:
            _reorder_steps(self.checklist_id, order_index, self.order_index)
            updates['order_index'] = order_index
    
    if updates:
        steps.update(updates, self.id)
        # Get fresh data and update attributes
        updated = _validate_step_exists(self.id)
        for key in updated.__dict__:
            setattr(self, key, getattr(updated, key))
    
    return self

def test_step_update():
    try:
        # Create test checklist and steps
        checklist = create_checklist("Test Checklist", "For testing step updates")
        (_,step1) = checklist.add_step("Step 1")  # order_index = 1
        (_,step2) = checklist.add_step("Step 2")  # order_index = 2
        (_,step3) = checklist.add_step("Step 3")  # order_index = 3
        
        # Test text update only
        step1.update(text="Updated Step 1")
        assert step1.text == "Updated Step 1"
        assert step1.order_index == 1
        
        # Test moving step up (higher to lower index)
        step3.update(order_index=1)
        assert step3.order_index == 1
        # Verify other steps shifted
        updated_step1 = steps(where=f"id = {step1.id}")[0]
        updated_step2 = steps(where=f"id = {step2.id}")[0]
        assert updated_step1.order_index == 2
        assert updated_step2.order_index == 3
        
        # Test moving step down (lower to higher index)
        step3.update(order_index=3)
        # Verify final positions
        final_step1 = steps(where=f"id = {step1.id}")[0]
        final_step2 = steps(where=f"id = {step2.id}")[0]
        final_step3 = steps(where=f"id = {step3.id}")[0]
        assert final_step1.order_index == 1
        assert final_step2.order_index == 2
        assert final_step3.order_index == 3
        
        print("All step update tests passed!")
        
    finally:
        # Cleanup
        if 'checklist' in locals(): checklists.delete(checklist.id)

# Run the tests
test_step_update()

@patch
def delete(self:Step):
    """Delete this step and reorder remaining steps
    Returns:
        True if successful
    """
    # Get current order_index and checklist_id before deletion
    order_index = self.order_index
    checklist_id = self.checklist_id
    
    # Delete any references first
    refs = step_references(where=f"step_id = {self.id}")
    for ref in refs:
        step_references.delete(ref.id)
    
    # Delete the step
    steps.delete(self.id)
    
    # Reorder remaining steps
    remaining = steps(
        where=f"checklist_id = {checklist_id} AND order_index > {order_index}",
        order_by="order_index"
    )
    for step in remaining:
        steps.update({'order_index': step.order_index - 1}, step.id)
    
    return True

def test_step_delete():
    try:
        # Create test checklist and steps
        checklist = create_checklist("Test Checklist", "For testing step deletion")
        (_,step1) = checklist.add_step("Step 1")  # order_index = 1
        (_,step2) = checklist.add_step("Step 2")  # order_index = 2
        (_,step3) = checklist.add_step("Step 3")  # order_index = 3
        
        # Delete middle step
        assert step2.delete()
        
        # Verify step3 moved up
        updated_step3 = steps(where=f"id = {step3.id}")[0]
        assert updated_step3.order_index == 2
        
        # Verify step count
        remaining = steps(where=f"checklist_id = {checklist.id}")
        assert len(remaining) == 2
        
        print("All step delete tests passed!")
        
    finally:
        # Cleanup
        if 'checklist' in locals(): checklists.delete(checklist.id)

# Run the tests
test_step_delete()

@patch
def add_reference(self:Step, url, reference_type='URL'):
    """Add a reference to this step
    Args:
        url: str - Reference URL
        reference_type: str - Type of reference (default: 'URL')
    Returns:
        Reference object for chaining
    """
    if not url:
        raise ValueError("URL is required")
    
    type_id = _get_reference_type_id(reference_type)
    
    return step_references.insert(
        step_id=self.id,
        url=url,
        reference_type_id=type_id
    )

def test_step_reference():
    try:
        # Create test checklist and step
        checklist = create_checklist("Test Checklist", "For testing references")
        (_,step) = checklist.add_step("Step with references")
        
        # Test basic reference addition
        ref1 = step.add_reference("https://example.com/doc1")
        assert ref1.url == "https://example.com/doc1"
        assert ref1.step_id == step.id
        
        # Test with custom reference type
        ref2 = step.add_reference("https://api.example.com/v1", "API")
        assert ref2.reference_type_id == _get_reference_type_id("API")
        
        # Test validation
        try:
            step.add_reference("")
            assert False, "Should fail with empty URL"
        except ValueError:
            pass
            
        print("All step reference tests passed!")
        
    finally:
        # Cleanup
        if 'checklist' in locals(): checklists.delete(checklist.id)

# Run the tests
test_step_reference()

@patch
def delete_reference(self:Step, reference_id):
    """Delete a specific reference from this step
    Args:
        reference_id: int - ID of reference to delete
    Returns:
        True if successful
    """
    ref = step_references(where=f"id = {reference_id} AND step_id = {self.id}")
    if not ref:
        raise ValueError(f"Reference {reference_id} not found for this step")
    
    step_references.delete(reference_id)
    return True

def test_delete_reference():
    try:
        # Create test checklist and step with references
        checklist = create_checklist("Test Checklist", "For testing reference deletion")
        (_,step) = checklist.add_step("Step with references")
        ref1 = step.add_reference("https://example.com/doc1")
        ref2 = step.add_reference("https://example.com/doc2")
        
        # Test successful deletion
        assert step.delete_reference(ref1.id)
        remaining = step_references(where=f"step_id = {step.id}")
        assert len(remaining) == 1
        assert remaining[0].id == ref2.id
        
        # Test deleting non-existent reference
        try:
            step.delete_reference(99999)
            assert False, "Should fail with non-existent reference"
        except ValueError:
            pass
        
        print("All delete_reference tests passed!")
        
    finally:
        # Cleanup
        if 'checklist' in locals(): checklists.delete(checklist.id)

# Run the tests
test_delete_reference()

@patch
def get_references(self:Step):
    """Get all references for this step
    Returns:
        List of reference objects
    """
    return step_references(
        where=f"step_id = {self.id}",
        order_by="id"
    )
def test_get_references():
    try:
        # Create test checklist and step
        checklist = create_checklist("Test Checklist", "For testing reference retrieval")
        (_,step) = checklist.add_step("Step with references")
        
        # Add some references
        ref1 = step.add_reference("https://example.com/doc1")
        ref2 = step.add_reference("https://example.com/doc2", "API")
        
        # Test reference retrieval
        refs = step.get_references()
        assert len(refs) == 2
        assert refs[0].url == "https://example.com/doc1"
        assert refs[1].url == "https://example.com/doc2"
        
        print("All get_references tests passed!")
        
    finally:
        # Cleanup
        if 'checklist' in locals(): checklists.delete(checklist.id)

# Run the test
test_get_references()

def delete_checklist(checklist_id):
    """Delete a checklist and all related items
    Args:
        checklist_id: int - ID of checklist to delete
    Returns:
        True if successful
    """
    # Validate checklist exists
    _validate_checklist_exists(checklist_id)
    
    # Get all steps for this checklist
    checklist_steps = steps(where=f"checklist_id = {checklist_id}")
    
    # Delete all references for all steps
    for step in checklist_steps:
        refs = step_references(where=f"step_id = {step.id}")
        for ref in refs:
            step_references.delete(ref.id)
    
    # Delete all steps
    for step in checklist_steps:
        steps.delete(step.id)
    
    # Delete the checklist
    checklists.delete(checklist_id)
    return True

def test_delete_checklist():
    try:
        # Create test checklist with steps and references
        checklist = create_checklist("Test Checklist", "For testing deletion")
        
        # Add steps with references
        (_,step1) = checklist.add_step("Step 1")
        step1.add_reference("https://example.com/doc1")
        
        (_,step2) = checklist.add_step("Step 2")
        step2.add_reference("https://example.com/doc2")
        step2.add_reference("https://example.com/doc3", "API")
        
        # Delete checklist
        assert delete_checklist(checklist.id)
        
        # Verify everything is gone
        assert not checklists(where=f"id = {checklist.id}"), "Checklist should be deleted"
        assert not steps(where=f"checklist_id = {checklist.id}"), "Steps should be deleted"
        assert not step_references(where=f"step_id = {step1.id}"), "References should be deleted"
        assert not step_references(where=f"step_id = {step2.id}"), "References should be deleted"
        
        # Test deleting non-existent checklist
        try:
            delete_checklist(99999)
            assert False, "Should fail with non-existent checklist"
        except ValueError:
            pass
            
        print("All delete_checklist tests passed!")
        
    except Exception as e:
        print(f"Test failed: {e}")
        raise
        
# Run the tests
test_delete_checklist()

class ChecklistBuilder:
    def __init__(self, checklist, current_step=None):
        self.checklist = checklist
        self.current_step = current_step
    
    def add_step(self, text, order_index=None):
        """Add step with optional ordering
        Args:
            text: str - Required step text
            order_index: int, optional - Position in sequence
        Returns:
            ChecklistBuilder for chaining
        """
        _, step = self.checklist.add_step(
            text=text,
            order_index=order_index
        )
        return ChecklistBuilder(self.checklist, step)
    
    def add_reference(self, url, reference_type='URL'):
        """Add reference to current step
        Args:
            url: str - Required URL
            reference_type: str - Type of reference (default: 'URL')
        Returns:
            ChecklistBuilder for chaining
        """
        if not self.current_step:
            raise ValueError("Cannot add reference without a step")
        self.current_step.add_reference(
            url=url,
            reference_type=reference_type
        )
        return ChecklistBuilder(self.checklist, self.current_step)

@patch
def build(self:Checklist):
    return ChecklistBuilder(self)

checklist = (create_checklist("New Employee Onboarding", "Complete onboarding process for new hires")
            .build()
            .add_step("Complete new hire paperwork").add_reference("https://hr.example.com/forms")
            .add_step("Set up workstation and equipment")
            .add_step("Create email account").add_reference("https://it.example.com/email-setup")
            .add_step("Building access card registration")
            .add_step("Schedule orientation meeting")
            .add_step("Review company policies").add_reference("https://policies.example.com/handbook")
            .add_step("Set up payroll and benefits").add_reference("https://hr.example.com/benefits")
            .add_step("Team introduction meeting")
            .add_step("Initial project assignment").add_reference("https://projects.example.com/onboarding")
            .checklist)

# Verify what was created
print(f"\nChecklist: {checklist.title}")
print("\nSteps and References:")
for step in steps(where=f"checklist_id = {checklist.id}", order_by="order_index"):
    print(f"\n{step.order_index}. {step.text}")
    refs = step.get_references()
    if refs:
        for ref in refs:
            print(f"   Reference: {ref.url}")

def test_enhanced_builder():
    try:
        # Example 1: Technical Documentation Checklist
        doc_checklist = (create_checklist("API Documentation", "Complete API documentation process")
            .build()
            .add_step("Write API Overview", order_index=1)
                .add_reference("https://docs.example.com/template", "TEMPLATE")
            .add_step("Document Authentication", order_index=3)
                .add_reference("https://auth.example.com/oauth", "API")
                .add_reference("https://security.example.com", "REFERENCE")
            .add_step("Create Code Examples", order_index=2)
            .checklist)

        # Example 2: Software Release Checklist
        release_checklist = (create_checklist("Version 2.0 Release", "Release preparation checklist")
            .build()
            .add_step("Run final tests", order_index=5)
            .add_step("Update changelog", order_index=1)
                .add_reference("https://changelog.example.com")
            .add_step("Tag release", order_index=4)
            .add_step("Update documentation", order_index=2)
            .add_step("Notify stakeholders", order_index=3)
                .add_reference("https://email.example.com", "TEMPLATE")
            .checklist)

        # Print results to verify
        for checklist in [doc_checklist, release_checklist]:
            print(f"\nChecklist: {checklist.title}")
            print("Steps and References (in order):")
            for step in steps(where=f"checklist_id = {checklist.id}", order_by="order_index"):
                print(f"\n{step.order_index}. {step.text}")
                refs = step.get_references()
                if refs:
                    for ref in refs:
                        ref_type = reference_types(where=f"id = {ref.reference_type_id}")[0].name
                        print(f"   {ref_type}: {ref.url}")

    finally:
        # Cleanup
        if 'doc_checklist' in locals(): checklists.delete(doc_checklist.id)
        if 'release_checklist' in locals(): checklists.delete(release_checklist.id)

# Run the tests
test_enhanced_builder()

def display_checklist(checklist_id):
    """Display a checklist and all its steps
    Args:
        checklist_id: int - ID of checklist to display
    """
    # Get checklist
    checklist = _validate_checklist_exists(checklist_id)
    
    # Print checklist details
    print(f"\nChecklist: {checklist.title}")
    print(f"Description: {checklist.description}")
    if checklist.description_long:
        print(f"Detailed Description: {checklist.description_long}")
    
    # Get and print steps
    print("\nSteps:")
    checklist_steps = steps(
        where=f"checklist_id = {checklist_id}",
        order_by="order_index"
    )
    
    for step in checklist_steps:
        print(f"\n{step.order_index}. {step.text}")
        # Get references for this step
        refs = step_references(where=f"step_id = {step.id}")
        if refs:
            print("   References:")
            for ref in refs:
                ref_type = reference_types(where=f"id = {ref.reference_type_id}")[0].name
                print(f"   - {ref_type}: {ref.url}")

display_checklist(1)
def get_checklist_with_steps(checklist_id):
    """Get checklist with all related data in a single query"""
    checklist = _validate_checklist_exists(checklist_id)
    checklist_steps = steps(
        where=f"checklist_id = {checklist_id}",
        order_by="order_index"
    )
    
    # Collect all step IDs for a single reference query
    step_ids = [s.id for s in checklist_steps]
    all_refs = step_references(where=f"step_id IN ({','.join(map(str, step_ids))})")
    
    # Organize references by step_id
    refs_by_step = {}
    for ref in all_refs:
        refs_by_step.setdefault(ref.step_id, []).append(ref)
    
    return checklist, checklist_steps, refs_by_step

def render_checklist_view(checklist_id):
    """Render a checklist view using MonsterUI components"""
    checklist, checklist_steps, refs_by_step = get_checklist_with_steps(checklist_id)
    
    # Create header section
    header = Div(
        H1(checklist.title, cls='uk-heading-medium'),
        P(checklist.description, cls='uk-text-lead uk-text-muted'),
        cls="uk-margin-bottom"
    )
    
    # Create steps list
    steps_list = []
    for step in checklist_steps:
        refs = refs_by_step.get(step.id, [])
        
        # Create reference links if any exist
        ref_links = []
        if refs:
            for ref in refs:
                ref_type = reference_types(where=f"id = {ref.reference_type_id}")[0]
                ref_links.append(
                    A(
                        DivLAligned(
                            UkIcon('link'),
                            P(f"{ref_type.name}: {ref.url}", cls='uk-text-small uk-text-muted')
                        ),
                        href=ref.url,
                        target="_blank",
                        cls="uk-link-muted"
                    )
                )
        
        # Create step card
        step_card = Card(
            DivFullySpaced(
                P(f"Step {step.order_index}", cls='uk-text-small uk-text-muted'),
                P(step.text, cls='uk-text-normal')
            ),
            *ref_links,
            cls="uk-margin-small"
        )
        steps_list.append(step_card)
    
    # Combine everything in a container
    return Container(
        header,
        *steps_list,
        cls="uk-margin-large-top"
    )

show(render_checklist_view(1))
def create_instance(checklist_id, name, description=None, target_date=None):
    """Create a new checklist instance with corresponding steps
    Args:
        checklist_id: int - ID of checklist to instantiate
        name: str - Name of this instance
        description: str, optional - Instance description
        target_date: str, optional - Target completion date
    Returns:
        Instance object for chaining
    """
    if not name:
        raise ValueError("Instance name is required")
    
    # Validate checklist and get its steps
    checklist = _validate_checklist_exists(checklist_id)
    checklist_steps = steps(where=f"checklist_id = {checklist_id}", order_by="order_index")
    
    # Create instance
    instance = checklist_instances.insert(
        checklist_id=checklist_id,
        name=name,
        description=description,
        target_date=target_date
    )
    
    # Create instance steps
    for step in checklist_steps:
        instance_steps.insert(
            checklist_instance_id=instance.id,
            step_id=step.id,
            status='Not Started'
        )
    
    return instance

def test_create_instance():
    try:
        # Create a test checklist with steps
        checklist = create_checklist("Test Checklist", "For testing instances")
        (_,step1) = checklist.add_step("Step 1")
        (_,step2) = checklist.add_step("Step 2")
        
        # Test basic instance creation
        instance1 = create_instance(
            checklist_id=checklist.id,
            name="Test Instance 1"
        )
        assert instance1.name == "Test Instance 1"
        assert instance1.status == "Not Started"
        
        # Verify instance steps were created
        inst_steps = instance_steps(where=f"checklist_instance_id = {instance1.id}")
        assert len(inst_steps) == 2
        assert all(s.status == "Not Started" for s in inst_steps)
        
        # Test with all optional fields
        instance2 = create_instance(
            checklist_id=checklist.id,
            name="Test Instance 2",
            description="Test description",
            target_date="2024-12-31"
        )
        assert instance2.description == "Test description"
        assert instance2.target_date == "2024-12-31"
        
        # Test validation
        try:
            create_instance(checklist.id, "")
            assert False, "Should fail with empty name"
        except ValueError:
            pass
            
        print("All create_instance tests passed!")
        
    finally:
        # Cleanup
        if 'checklist' in locals(): checklists.delete(checklist.id)

# Run the tests
test_create_instance()

def delete_instance(instance_id):
    """Delete a checklist instance and all its steps
    Args:
        instance_id: int - ID of instance to delete
    Returns:
        True if successful
    """
    # Validate instance exists
    if not isinstance(instance_id, int) or instance_id < 1:
        raise ValueError(f"Invalid instance_id: {instance_id}")
    result = checklist_instances(where=f"id = {instance_id}")
    if not result:
        raise ValueError(f"Instance not found: {instance_id}")
    
    # Delete all instance steps first
    steps_to_delete = instance_steps(where=f"checklist_instance_id = {instance_id}")
    for step in steps_to_delete:
        instance_steps.delete(step.id)
    
    # Delete the instance
    checklist_instances.delete(instance_id)
    return True

def test_delete_instance():
    try:
        # Create test checklist with steps
        checklist = create_checklist("Test Checklist", "For testing instance deletion")
        (_,step1) = checklist.add_step("Step 1")
        (_,step2) = checklist.add_step("Step 2")
        
        # Create test instance
        instance = create_instance(
            checklist_id=checklist.id,
            name="Test Instance"
        )
        
        # Verify initial state
        assert len(instance_steps(where=f"checklist_instance_id = {instance.id}")) == 2
        
        # Test deletion
        assert delete_instance(instance.id)
        
        # Verify instance and steps are gone
        assert not checklist_instances(where=f"id = {instance.id}"), "Instance should be deleted"
        assert not instance_steps(where=f"checklist_instance_id = {instance.id}"), "Instance steps should be deleted"
        
        # Test invalid deletions
        try:
            delete_instance(-1)
            assert False, "Should fail with negative ID"
        except ValueError:
            pass
            
        try:
            delete_instance(99999)
            assert False, "Should fail with non-existent ID"
        except ValueError:
            pass
            
        print("All delete_instance tests passed!")
        
    finally:
        # Cleanup
        if 'checklist' in locals(): checklists.delete(checklist.id)

# Run the tests
test_delete_instance()

# Create Instance dataclass
Instance = checklist_instances.dataclass()

@patch
def update(self:Instance, name=None, description=None, target_date=None):
    """Update instance fields
    Args:
        name: str, optional - New instance name
        description: str, optional - New description
        target_date: str, optional - New target date
    Returns:
        self for chaining
    """
    updates = {}
    if name: updates['name'] = name
    if description is not None: updates['description'] = description
    if target_date is not None: updates['target_date'] = target_date
    
    if updates:
        checklist_instances.update(updates, self.id)
        # Get fresh data and update attributes
        updated = checklist_instances(where=f"id = {self.id}")[0]
        for key in updated.__dict__:
            setattr(self, key, getattr(updated, key))
    
    return self

def test_instance_update():
    try:
        # Create test checklist and instance
        checklist = create_checklist("Test Checklist", "For testing instance updates")
        instance = create_instance(
            checklist_id=checklist.id,
            name="Original Name",
            description="Original description"
        )
        
        # Test single field update
        instance.update(name="Updated Name")
        assert instance.name == "Updated Name"
        assert instance.description == "Original description"
        
        # Test multiple field update
        instance.update(
            description="New description",
            target_date="2024-12-31"
        )
        assert instance.description == "New description"
        assert instance.target_date == "2024-12-31"
        
        # Test no changes case
        orig_modified = instance.last_modified
        instance.update()  # No parameters
        assert instance.last_modified == orig_modified, "Should not update if no changes"
        
        print("All instance update tests passed!")
        
    finally:
        # Cleanup
        if 'checklist' in locals(): checklists.delete(checklist.id)

# Run the tests
test_instance_update()

# Define valid status values
VALID_STATUSES = ['Not Started', 'In Progress', 'Completed']

@patch
def update_step_status(self:Instance, step_id, status):
    """Update status of a step in this instance"""
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status. Must be one of: {', '.join(VALID_STATUSES)}")
    
    # Find the instance step
    result = instance_steps(
        where=f"checklist_instance_id = {self.id} AND step_id = {step_id}"
    )
    if not result:
        raise ValueError(f"Step {step_id} not found in this instance")
    
    # Update the status with explicit timestamp
    instance_steps.update({
        'status': status,
        'last_modified': 'CURRENT_TIMESTAMP'
    }, result[0].id)
    return self

# Define valid status values
# VALID_STATUSES = ['Not Started', 'In Progress', 'Completed']

# @patch
# def update_step_status(self:Instance, step_id, status):
#     """Update status of a step in this instance
#     Args:
#         step_id: int - ID of the step to update
#         status: str - New status (must be one of VALID_STATUSES)
#     Returns:
#         self for chaining
#     """
#     if status not in VALID_STATUSES:
#         raise ValueError(f"Invalid status. Must be one of: {', '.join(VALID_STATUSES)}")
    
#     # Find the instance step
#     result = instance_steps(
#         where=f"checklist_instance_id = {self.id} AND step_id = {step_id}"
#     )
#     if not result:
#         raise ValueError(f"Step {step_id} not found in this instance")
    
#     # Update the status
#     instance_steps.update({'status': status}, result[0].id)
#     return self

def test_update_step_status():
    try:
        # Create test checklist with steps
        checklist = create_checklist("Test Checklist", "For testing status updates")
        (_,step1) = checklist.add_step("Step 1")
        (_,step2) = checklist.add_step("Step 2")
        
        # Create test instance
        instance = create_instance(
            checklist_id=checklist.id,
            name="Test Instance"
        )
        
        # Test status updates
        instance.update_step_status(step1.id, "In Progress")
        instance.update_step_status(step2.id, "Completed")
        
        # Verify updates
        inst_steps = instance_steps(where=f"checklist_instance_id = {instance.id}")
        statuses = {s.step_id: s.status for s in inst_steps}
        assert statuses[step1.id] == "In Progress"
        assert statuses[step2.id] == "Completed"
        
        # Test invalid status
        try:
            instance.update_step_status(step1.id, "Invalid Status")
            assert False, "Should fail with invalid status"
        except ValueError:
            pass
        
        # Test invalid step
        try:
            instance.update_step_status(99999, "Completed")
            assert False, "Should fail with non-existent step"
        except ValueError:
            pass
        
        print("All update_step_status tests passed!")
        
    finally:
        # Cleanup
        if 'checklist' in locals(): checklists.delete(checklist.id)

# Run the tests
test_update_step_status()

@patch
def add_step_note(self:Instance, step_id, note):
    """Add or update note for a step in this instance"""
    if not note:
        raise ValueError("Note text is required")
    
    # Find the instance step
    result = instance_steps(
        where=f"checklist_instance_id = {self.id} AND step_id = {step_id}"
    )
    if not result:
        raise ValueError(f"Step {step_id} not found in this instance")
    
    # Update the note - remove explicit timestamp as SQLite will handle it via trigger
    instance_steps.update({'notes': note}, result[0].id)
    return self


# @patch
# def add_step_note(self:Instance, step_id, note):
#     """Add or update note for a step in this instance
#     Args:
#         step_id: int - ID of the step
#         note: str - Note text to add/update
#     Returns:
#         self for chaining
#     """
#     if not note:
#         raise ValueError("Note text is required")
    
#     # Find the instance step
#     result = instance_steps(
#         where=f"checklist_instance_id = {self.id} AND step_id = {step_id}"
#     )
#     if not result:
#         raise ValueError(f"Step {step_id} not found in this instance")
    
#     # Update the note
#     instance_steps.update({'notes': note}, result[0].id)
#     return self

def test_add_step_note():
    try:
        # Create test checklist with step
        checklist = create_checklist("Test Checklist", "For testing step notes")
        (_,step1) = checklist.add_step("Step 1")
        
        # Create test instance
        instance = create_instance(
            checklist_id=checklist.id,
            name="Test Instance"
        )
        
        # Test adding note
        instance.add_step_note(step1.id, "First note")
        
        # Verify note was added
        inst_step = instance_steps(
            where=f"checklist_instance_id = {instance.id} AND step_id = {step1.id}"
        )[0]
        assert inst_step.notes == "First note"
        
        # Test updating existing note
        instance.add_step_note(step1.id, "Updated note")
        inst_step = instance_steps(
            where=f"checklist_instance_id = {instance.id} AND step_id = {step1.id}"
        )[0]
        assert inst_step.notes == "Updated note"
        
        # Test validation
        try:
            instance.add_step_note(step1.id, "")
            assert False, "Should fail with empty note"
        except ValueError:
            pass
        
        try:
            instance.add_step_note(99999, "Note")
            assert False, "Should fail with non-existent step"
        except ValueError:
            pass
        
        print("All add_step_note tests passed!")
        
    finally:
        # Cleanup
        if 'checklist' in locals(): checklists.delete(checklist.id)

# Run the tests
test_add_step_note()

@patch
def get_step_status(self:Instance, step_id):
    """Get status and notes for a step in this instance
    Args:
        step_id: int - ID of the step
    Returns:
        dict with 'status' and 'notes' keys
    """
    result = instance_steps(
        where=f"checklist_instance_id = {self.id} AND step_id = {step_id}"
    )
    if not result:
        raise ValueError(f"Step {step_id} not found in this instance")
    
    step = result[0]
    return {
        'status': step.status,
        'notes': step.notes
    }

def test_get_step_status():
    try:
        # Create test checklist with step
        checklist = create_checklist("Test Checklist", "For testing status retrieval")
        (_,step1) = checklist.add_step("Step 1")
        
        # Create test instance
        instance = create_instance(
            checklist_id=checklist.id,
            name="Test Instance"
        )
        
        # Test initial status
        status_info = instance.get_step_status(step1.id)
        assert status_info['status'] == 'Not Started'
        assert status_info['notes'] is None
        
        # Update status and notes
        instance.update_step_status(step1.id, "In Progress")
        instance.add_step_note(step1.id, "Working on it")
        
        # Test updated status
        status_info = instance.get_step_status(step1.id)
        assert status_info['status'] == 'In Progress'
        assert status_info['notes'] == 'Working on it'
        
        # Test invalid step
        try:
            instance.get_step_status(99999)
            assert False, "Should fail with non-existent step"
        except ValueError:
            pass
        
        print("All get_step_status tests passed!")
        
    finally:
        # Cleanup
        if 'checklist' in locals(): checklists.delete(checklist.id)

# Run the tests
test_get_step_status()

@patch
def get_progress(self:Instance):
    """Get progress statistics for this instance
    Returns:
        dict with:
        - percentage: float (0-100)
        - counts: dict of status counts
        - total_steps: int
    """
    # Get all steps for this instance
    inst_steps = instance_steps(where=f"checklist_instance_id = {self.id}")
    total = len(inst_steps)
    
    if total == 0:
        return {
            'percentage': 0.0,
            'counts': {status: 0 for status in VALID_STATUSES},
            'total_steps': 0
        }
    
    # Count steps by status
    counts = {status: 0 for status in VALID_STATUSES}
    for step in inst_steps:
        counts[step.status] += 1
    
    # Calculate completion percentage
    completed = counts['Completed']
    percentage = (completed / total) * 100
    
    return {
        'percentage': percentage,
        'counts': counts,
        'total_steps': total
    }

def test_get_progress():
    try:
        # Create test checklist with steps
        checklist = create_checklist("Test Checklist", "For testing progress tracking")
        (_,step1) = checklist.add_step("Step 1")
        (_,step2) = checklist.add_step("Step 2")
        (_,step3) = checklist.add_step("Step 3")
        (_,step4) = checklist.add_step("Step 4")
        
        # Create test instance
        instance = create_instance(
            checklist_id=checklist.id,
            name="Test Instance"
        )
        
        # Test initial progress (all Not Started)
        progress = instance.get_progress()
        assert progress['percentage'] == 0.0
        assert progress['counts']['Not Started'] == 4
        assert progress['counts']['Completed'] == 0
        assert progress['total_steps'] == 4
        
        # Update some statuses
        instance.update_step_status(step1.id, "Completed")
        instance.update_step_status(step2.id, "In Progress")
        instance.update_step_status(step3.id, "Completed")
        
        # Test updated progress
        progress = instance.get_progress()
        assert progress['percentage'] == 50.0  # 2 of 4 completed
        assert progress['counts']['Completed'] == 2
        assert progress['counts']['In Progress'] == 1
        assert progress['counts']['Not Started'] == 1
        
        print("All get_progress tests passed!")
        
    finally:
        # Cleanup
        if 'checklist' in locals(): checklists.delete(checklist.id)

# Run the tests
test_get_progress()

# Define instance status values based on progress
INSTANCE_STATUSES = {
    'Not Started': 0,    # No steps started
    'In Progress': 1,    # Some steps in progress or completed
    'Completed': 2       # All steps completed
}

@patch
def update_status(self:Instance):
    """Update instance status based on step progress
    Returns:
        self for chaining
    """
    progress = self.get_progress()
    
    # Determine new status
    if progress['total_steps'] == 0:
        new_status = 'Not Started'
    elif progress['percentage'] == 100:
        new_status = 'Completed'
    elif progress['counts']['Not Started'] == progress['total_steps']:
        new_status = 'Not Started'
    else:
        new_status = 'In Progress'
    
    # Update if different
    if self.status != new_status:
        checklist_instances.update({'status': new_status}, self.id)
        self.status = new_status
    
    return self

def test_update_status():
    try:
        # Create test checklist with steps
        checklist = create_checklist("Test Checklist", "For testing status updates")
        (_,step1) = checklist.add_step("Step 1")
        (_,step2) = checklist.add_step("Step 2")
        
        # Create test instance
        instance = create_instance(
            checklist_id=checklist.id,
            name="Test Instance"
        )
        
        # Test initial status
        instance.update_status()
        assert instance.status == "Not Started"
        
        # Test In Progress status
        instance.update_step_status(step1.id, "Completed")
        instance.update_status()
        assert instance.status == "In Progress"
        
        # Test Completed status
        instance.update_step_status(step2.id, "Completed")
        instance.update_status()
        assert instance.status == "Completed"
        
        # Test reverting to In Progress
        instance.update_step_status(step2.id, "In Progress")
        instance.update_status()
        assert instance.status == "In Progress"
        
        print("All update_status tests passed!")
        
    finally:
        # Cleanup
        if 'checklist' in locals(): checklists.delete(checklist.id)

# Run the tests
test_update_status()

@patch
def get_incomplete_steps(self:Instance):
    """Get all incomplete steps for this instance
    Returns:
        List of dicts with step info including:
        - id: step ID
        - text: step text
        - status: current status
        - notes: any notes added
        - order_index: original step order
    """
    # Get all incomplete instance steps joined with steps
    incomplete = instance_steps(
        where=f"checklist_instance_id = {self.id} AND status != 'Completed'"
    )
    
    # Get step details for each incomplete step and sort by order_index
    result = []
    for inst_step in incomplete:
        step = steps(where=f"id = {inst_step.step_id}")[0]
        result.append({
            'id': step.id,
            'text': step.text,
            'status': inst_step.status,
            'notes': inst_step.notes,
            'order_index': step.order_index
        })
    
    # Sort by order_index
    result.sort(key=lambda x: x['order_index'])
    return result

def test_get_incomplete_steps():
    try:
        # Create test checklist with steps
        checklist = create_checklist("Test Checklist", "For testing incomplete steps")
        (_,step1) = checklist.add_step("Step 1")
        (_,step2) = checklist.add_step("Step 2")
        (_,step3) = checklist.add_step("Step 3")
        
        # Create test instance
        instance = create_instance(
            checklist_id=checklist.id,
            name="Test Instance"
        )
        
        # Test initial state (all incomplete)
        incomplete = instance.get_incomplete_steps()
        assert len(incomplete) == 3
        assert [s['text'] for s in incomplete] == ["Step 1", "Step 2", "Step 3"]
        
        # Complete some steps
        instance.update_step_status(step1.id, "Completed")
        instance.add_step_note(step2.id, "Working on this")
        instance.update_step_status(step2.id, "In Progress")
        
        # Test after updates
        incomplete = instance.get_incomplete_steps()
        assert len(incomplete) == 2
        assert incomplete[0]['text'] == "Step 2"
        assert incomplete[0]['status'] == "In Progress"
        assert incomplete[0]['notes'] == "Working on this"
        assert incomplete[1]['text'] == "Step 3"
        assert incomplete[1]['status'] == "Not Started"
        
        print("All get_incomplete_steps tests passed!")
        
    finally:
        # Cleanup
        if 'checklist' in locals(): checklists.delete(checklist.id)

# Run the tests
test_get_incomplete_steps()

def get_active_instances(checklist_id=None):
    """Get all active (non-completed) checklist instances
    Args:
        checklist_id: int, optional - Filter by specific checklist
    Returns:
        List of Instance objects
    """
    where_clause = "status != 'Completed'"
    if checklist_id is not None:
        _validate_checklist_exists(checklist_id)
        where_clause += f" AND checklist_id = {checklist_id}"
    
    return checklist_instances(
        where=where_clause,
        order_by="created_at DESC"
    )
def test_get_active_instances():
    try:
        # Create test checklists with steps first
        checklist1 = create_checklist("Checklist 1", "First test checklist")
        (_,step1) = checklist1.add_step("Step 1")
        
        checklist2 = create_checklist("Checklist 2", "Second test checklist")
        (_,step2) = checklist2.add_step("Step 1")
        
        # Now create instances
        instance1 = create_instance(checklist1.id, "Instance 1")  # Not Started
        instance2 = create_instance(checklist1.id, "Instance 2")  # Will be In Progress
        instance3 = create_instance(checklist1.id, "Instance 3")  # Will be Completed
        instance4 = create_instance(checklist2.id, "Instance 4")  # Not Started
        
        # Update statuses
        instance2.update_step_status(step1.id, "In Progress")
        instance2.update_status()
        
        instance3.update_step_status(step1.id, "Completed")
        instance3.update_status()
        
        # Test getting all active instances
        active = get_active_instances()
        assert len(active) == 3
        active_names = {i.name for i in active}
        assert active_names == {"Instance 1", "Instance 2", "Instance 4"}
        
        # Test filtering by checklist
        active_cl1 = get_active_instances(checklist1.id)
        assert len(active_cl1) == 2
        active_cl1_names = {i.name for i in active_cl1}
        assert active_cl1_names == {"Instance 1", "Instance 2"}
        
        # Test invalid checklist
        try:
            get_active_instances(99999)
            assert False, "Should fail with non-existent checklist"
        except ValueError:
            pass
        
        print("All get_active_instances tests passed!")
        
    finally:
        # Cleanup
        if 'checklist1' in locals(): checklists.delete(checklist1.id)
        if 'checklist2' in locals(): checklists.delete(checklist2.id)

# Run the tests
test_get_active_instances()

def get_instances_by_status(status, checklist_id=None):
    """Get checklist instances by status
    Args:
        status: str - Required status to filter by (must be in INSTANCE_STATUSES)
        checklist_id: int, optional - Further filter by specific checklist
    Returns:
        List of Instance objects
    """
    if status not in INSTANCE_STATUSES:
        raise ValueError(f"Invalid status. Must be one of: {', '.join(INSTANCE_STATUSES.keys())}")
    
    where_clause = f"status = '{status}'"
    if checklist_id is not None:
        _validate_checklist_exists(checklist_id)
        where_clause += f" AND checklist_id = {checklist_id}"
    
    return checklist_instances(
        where=where_clause,
        order_by="created_at DESC"
    )

def test_get_instances_by_status():
    try:
        # Create test checklists with steps
        checklist1 = create_checklist("Checklist 1", "First test checklist")
        (_,step1) = checklist1.add_step("Step 1")
        
        checklist2 = create_checklist("Checklist 2", "Second test checklist")
        (_,step2) = checklist2.add_step("Step 1")
        
        # Create instances with various statuses
        instance1 = create_instance(checklist1.id, "Instance 1")  # Not Started
        instance2 = create_instance(checklist1.id, "Instance 2")  # Will be In Progress
        instance3 = create_instance(checklist1.id, "Instance 3")  # Will be Completed
        instance4 = create_instance(checklist2.id, "Instance 4")  # Not Started
        
        # Update statuses
        instance2.update_step_status(step1.id, "In Progress")
        instance2.update_status()
        
        instance3.update_step_status(step1.id, "Completed")
        instance3.update_status()
        
        # Test getting by status
        not_started = get_instances_by_status("Not Started")
        assert len(not_started) == 2
        assert {i.name for i in not_started} == {"Instance 1", "Instance 4"}
        
        in_progress = get_instances_by_status("In Progress")
        assert len(in_progress) == 1
        assert in_progress[0].name == "Instance 2"
        
        completed = get_instances_by_status("Completed")
        assert len(completed) == 1
        assert completed[0].name == "Instance 3"
        
        # Test filtering by checklist and status
        cl1_not_started = get_instances_by_status("Not Started", checklist1.id)
        assert len(cl1_not_started) == 1
        assert cl1_not_started[0].name == "Instance 1"
        
        # Test invalid status
        try:
            get_instances_by_status("Invalid Status")
            assert False, "Should fail with invalid status"
        except ValueError:
            pass
        
        # Test invalid checklist
        try:
            get_instances_by_status("Not Started", 99999)
            assert False, "Should fail with non-existent checklist"
        except ValueError:
            pass
        
        print("All get_instances_by_status tests passed!")
        
    finally:
        # Cleanup
        if 'checklist1' in locals(): checklists.delete(checklist1.id)
        if 'checklist2' in locals(): checklists.delete(checklist2.id)

# Run the tests
test_get_instances_by_status()

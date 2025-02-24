from httpx import get as xget, post as xpost
import os
from fasthtml.common import *
from fasthtml.common import RedirectResponse as redirect
from monsterui.all import *
from datetime import datetime
import argparse
import sqlite3
from time import sleep
from fastcore.basics import AttrDict, patch
from Internal_functions import (
    _validate_checklist_exists,
    _validate_step_exists,
    _get_reference_type_id,
    _get_next_order_index,
    _reorder_steps
)
from main import (
    checklists, 
    steps, 
    reference_types,
    step_references,
    checklist_instances,
    instance_steps,
    Step, 
    Checklist, 
    StepReference, 
    Instance
)

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














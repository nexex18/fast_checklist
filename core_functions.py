# Standard library imports
import re
from datetime import datetime
from enum import Enum
from urllib.parse import urlparse

# Third-party library imports
import pendulum
import bleach

# FastHTML and related imports
from fasthtml.common import (
    database, 
    patch
)
from fastcore.basics import AttrDict
from fastcore.test import test_eq

# Database and model imports (from main)
from main import (
    checklists, 
    steps, 
    reference_types,
    step_references,
    checklist_instances,
    instance_steps
)

# Optional imports if needed
import sqlite3
import os

# Rest of your file remains the same

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


def format_instance_url(name: str, guid: str) -> str:
    """
    Format a URL-safe instance path from a name and GUID
    """
    # Step 1: Clean and normalize the name
    slug = name.strip().lower()
    
    # Step 2: Replace special characters with dashes
    import re
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    
    # Step 3: Remove leading/trailing dashes and collapse multiple dashes
    slug = re.sub(r'-+', '-', slug).strip('-')
    
    # Step 4: Construct the final URL
    return f"/i/{slug}/{guid}"

class TimeFormat(Enum):
    short = 'short'
    long = 'long'
    relative = 'relative'

def format_timestamp(ts, fmt:TimeFormat=TimeFormat.short, tz:str='UTC') -> str:
    "Format timestamp in user-friendly way with timezone support"
    if ts == 'CURRENT_TIMESTAMP': 
        ts = pendulum.now(tz)
    # Handle different input types
    if isinstance(ts, (int, float)):
        ts = pendulum.from_timestamp(ts)
    elif isinstance(ts, str):
        ts = pendulum.parse(ts)
    elif not isinstance(ts, pendulum.DateTime):
        ts = pendulum.instance(ts)
    
    now = pendulum.now(tz)
    ts = ts.in_timezone(tz)
    
    # Today
    if ts.date() == now.date(): return ts.format('h:mm A')
    
    # Yesterday
    if ts.date() == now.subtract(days=1).date(): return f"Yesterday at {ts.format('h:mm A')}"
        
    # This week
    if ts.week_of_year == now.week_of_year: return ts.format('ddd, MMM D')
        
    # This year
    if ts.year == now.year: return ts.format('MMM D')
        
    # Different year
    return ts.format('MMM D, YYYY')


class ProgressFormat(Enum):
    number = 'number'      # "50"
    percent = 'percent'    # "50%"
    bar = 'bar'           # "[=====>----]"
    full = 'full'         # "[=====>----] 50%"

def format_progress_percentage(completed:int, total:int, fmt:ProgressFormat=ProgressFormat.percent) -> str:
    "Format progress as percentage with optional visual representation"
    if total == 0: return "0%" if fmt != ProgressFormat.number else "0"
    pct = round((completed / total) * 100)
    
    if fmt == ProgressFormat.number: return str(pct)
    if fmt == ProgressFormat.percent: return f"{pct}%"
    
    # Create progress bar
    width = 10
    filled = round(width * (completed / total))
    bar = f"[{'=' * filled}>{'-' * (width - filled)}]"
    
    if fmt == ProgressFormat.bar: return bar
    return f"{bar} {pct}%"



@patch
def get_checklist_with_stats(self:Checklist):
    "Get checklist with usage statistics"
    # Get steps count using L to leverage fastcore
    step_count = len(L(steps(where=f"checklist_id = {self.id}")))
    
    # Get instance counts 
    active = len(get_active_instances(self.id))
    completed = len(get_instances_by_status('Completed', self.id))
    
    return {
        'id': self.id,
        'title': self.title,
        'description': self.description,
        'description_long': self.description_long,
        'stats': {
            'total_steps': step_count,
            'active_instances': active,
            'completed_instances': completed,
            'last_modified': self.last_modified
        }
    }


@patch
def get_instance_with_details(self:Instance):
    "Get instance with all related data for display"
    # Get all steps with status
    instance_step_list = instance_steps(where=f"checklist_instance_id = {self.id}")
    steps_data = L(instance_step_list).map(lambda s: {
        'id': s.id,
        'text': steps[s.step_id].text,  # Get text from steps table using step_id
        'status': s.status,
        'notes': s.notes,
        'refs': L(step_references(where=f"step_id = {s.step_id}")),
        'last_modified': format_timestamp(s.last_modified)
    })
    
    return {
        'id': self.id,
        'name': self.name,
        'description': self.description,
        'created_at': format_timestamp(self.created_at),
        'target_date': format_timestamp(self.target_date) if self.target_date else None,
        'progress': format_progress_percentage(
            len(steps_data.filter(lambda s: s['status'] == 'Completed')),
            len(steps_data),
            fmt=ProgressFormat.full
        ),
        'steps': steps_data
    }


def _clean_md(s:str):
    "Clean string while preserving markdown"
    return bleach.clean(s, strip=True, 
                tags=['p','br','strong','em','ul','ol','li','code','pre','hr'],
                attributes={'*': ['class']},
                strip_comments=True,
                protocols=['http', 'https'])

def sanitize_user_input(x):
    "Sanitize user input while preserving markdown and structure"
    if isinstance(x, (int, float)): return x
    if x is None: return None
    if isinstance(x, str): 
        # Remove script tags and contents completely
        x = re.sub(r'<script.*?>.*?</script>', '', x, flags=re.DOTALL)
        return _clean_md(x)
    if isinstance(x, (list, L)): return type(x)(sanitize_user_input(i) for i in x)
    if isinstance(x, dict): return {k:sanitize_user_input(v) for k,v in x.items()}
    return x


def validate_instance_dates(target_date=None, tz='UTC', max_days=365):
    "Validate instance dates are within acceptable ranges"
    if target_date is None: return (True, None)
    
    # Convert to pendulum datetime if needed
    if isinstance(target_date, str): 
        target_date = pendulum.parse(target_date)
    
    now = pendulum.now(tz)
    
    # Must be in future
    if target_date < now:
        return (False, "Target date must be in future")
    
    # Check if too far in future
    if target_date > now.add(days=max_days):
        return (False, f"Target date cannot be more than {max_days} days in future")
        
    return (True, None)



def handle_view_mode_toggle(current_mode:str, data:dict, unsaved:bool=False):
    "Toggle between view/edit modes with state handling"
    if current_mode not in ('view', 'edit'): 
        raise ValueError(f"Invalid mode: {current_mode}")
    
    # Handle edit -> view transition with unsaved changes
    if current_mode == 'edit' and unsaved:
        return ('edit', Div(
            Alert("You have unsaved changes!", cls='uk-alert-warning'),
            Button("Discard Changes", 
                   hx_post=f"/toggle/{data['id']}/view",
                   cls='uk-button-danger'),
            Button("Keep Editing", 
                   hx_post=f"/toggle/{data['id']}/edit",
                   cls='uk-button-primary')
        ))
    
    # Toggle mode and return appropriate components
    new_mode = 'edit' if current_mode == 'view' else 'view'
    return (new_mode, 
            Form(data) if new_mode == 'edit' 
            else Container(data))




def _rank_results(matches:L, query:str) -> L:
    "Rank results based on match quality"
    def _score(c):
        title_match = query.lower() in c.title.lower()
        desc_match = c.description and query.lower() in c.description.lower()
        return (2 if title_match else 0) + (1 if desc_match else 0)
    
    return matches.sorted(key=_score, reverse=True)


def search_checklists(query:str, tags:list=None, limit:int=10) -> L:
    "Search checklists by query and optional tags"
    if not query or len(query.strip()) < 2: return L()
    
    # Clean query for SQL LIKE
    q = f"%{query.strip().lower()}%"
    
    # Search in titles and descriptions
    matches = L(checklists(where=f"LOWER(title) LIKE '{q}' OR LOWER(description) LIKE '{q}'"))
    
    # Search in steps content
    step_matches = L(steps(where=f"LOWER(text) LIKE '{q}'"))
    if step_matches:
        checklist_ids = step_matches.map(lambda s: s.checklist_id).unique()
        matches += L(checklists(where=f"id IN ({','.join(map(str,checklist_ids))})"))\
                  .filter(lambda c: c not in matches)
    
    return _rank_results(matches, query)[:limit]



def _calc_instance_progress(instance_id):
    "Calculate completion percentage for an instance"
    steps = L(instance_steps(where=f"checklist_instance_id = {instance_id}"))
    if not len(steps): return 0
    completed = len(steps.filter(lambda s: s.status == 'Completed'))
    progress = completed / len(steps)
    return progress


def search_instances(query:str, status=None, date_from=None, date_to=None, 
                    sort_by='created_at', limit=10) -> L:
    "Search instances with filters and sorting"
    if not query or len(query.strip()) < 2: return L()
    
    # First update all instance statuses to ensure consistency
    instances = L(checklist_instances(where=f"LOWER(name) LIKE '%{query.lower()}%'"))
    for inst in instances:
        inst_steps = L(instance_steps(where=f"checklist_instance_id = {inst.id}"))
        if len(inst_steps):
            completed = len(inst_steps.filter(lambda s: s.status == 'Completed'))
            current_status = 'Completed' if completed == len(inst_steps) else \
                           'In Progress' if completed > 0 else 'Not Started'
            if inst.status != current_status:
                checklist_instances.update({'status': current_status}, inst.id)
                inst.status = current_status
    
    # Apply filters
    if status:
        instances = instances.filter(lambda i: i.status == status)
    if date_from:
        instances = instances.filter(lambda i: i.created_at >= date_from)
    if date_to:
        instances = instances.filter(lambda i: i.created_at <= date_to)
    
    return instances.sorted(key=lambda i: (
        _calc_instance_progress(i.id) if sort_by == 'progress' 
        else getattr(i, sort_by)
    ), reverse=True)[:limit]



def get_active_instances_summary(days_due=7):
    "Get summary of active instances for dashboard"
    # Get non-completed instances and ensure status is current
    active = L(checklist_instances(where="status != 'Completed'"))
    if not len(active): return {'active_count': 0, 'due_soon': [], 'by_status': {}, 'completion_rate': 0}
    
    # Update status for each instance based on steps
    for inst in active:
        inst_steps = L(instance_steps(where=f"checklist_instance_id = {inst.id}"))
        if len(inst_steps):
            completed = len(inst_steps.filter(lambda s: s.status == 'Completed'))
            total = len(inst_steps)
            
            # Determine status based on completion
            new_status = 'Not Started'
            if completed == total: new_status = 'Completed'
            elif completed > 0: new_status = 'In Progress'
            
            # Update if different
            if inst.status != new_status:
                checklist_instances.update({'status': new_status}, inst.id)
                inst.status = new_status
    
    # Recalculate active instances after status updates
    active = L(checklist_instances(where="status != 'Completed'"))
    
    # Rest of the function remains same
    now = pendulum.now('UTC')
    due_cutoff = now.add(days=days_due)
    due_soon = active.filter(lambda i: i.target_date and 
                           pendulum.parse(i.target_date) <= due_cutoff)
    
    by_status = active.groupby(lambda i: i.status)
    status_counts = {k:len(v) for k,v in by_status.items()}
    
    completion_rates = [_calc_instance_progress(i.id) for i in active]
    avg_completion = sum(completion_rates) / len(completion_rates) if completion_rates else 0
    
    return {
        'active_count': len(active),
        'due_soon': due_soon,
        'by_status': status_counts,
        'completion_rate': avg_completion
    }



def verify_instance_state(instance_id=None, fix=False):
    "Verify and optionally fix instance data consistency"
    report = {'missing_steps': [], 'invalid_status': [], 
              'orphaned_records': [], 'fixes_applied': False}
    
    # Get instances to check
    instances = L(checklist_instances(where=f"id = {instance_id}")) if instance_id \
                else L(checklist_instances())
    
    for inst in instances:
        # Get expected steps from checklist
        checklist_steps = L(steps(where=f"checklist_id = {inst.checklist_id}"))
        instance_step_records = L(instance_steps(where=f"checklist_instance_id = {inst.id}"))
        
        # Check for missing steps
        for step in checklist_steps:
            if not instance_step_records.filter(lambda s: s.step_id == step.id):
                report['missing_steps'].append((inst.id, step.id))
                if fix:
                    instance_steps.insert({'checklist_instance_id': inst.id,
                                         'step_id': step.id,
                                         'status': 'Not Started'})
        
        # Check for orphaned records
        for inst_step in instance_step_records:
            if not checklist_steps.filter(lambda s: s.id == inst_step.step_id):
                report['orphaned_records'].append(inst_step.id)
                if fix: instance_steps.delete(inst_step.id)
        
        # Verify status consistency
        step_statuses = instance_step_records.attrgot('status')
        if all(s == 'Completed' for s in step_statuses) and inst.status != 'Completed':
            report['invalid_status'].append(inst.id)
            if fix: checklist_instances.update({'status': 'Completed'}, inst.id)
    
    if fix and (report['missing_steps'] or report['invalid_status'] or report['orphaned_records']):
        report['fixes_applied'] = True
    
    return report



# INTERNAL FUNCTIONS BELOW



def create_sample_data():
    "Create sample checklists, steps and instances for testing"
    add_reference_type(name='TEXT', description='Text reference or note')
    
    checklists_data = [
        ("Server Setup", "New server configuration", [
            ("Install OS", [
                ("URL", "https://docs.example.com/os"),
                ("TEXT", "Use Ubuntu 22.04 LTS with minimal server configuration")
            ], "Ubuntu 22.04"),
            ("Configure firewall", [
                ("TEXT", "Default ports: 22(SSH), 80(HTTP), 443(HTTPS), 5432(PostgreSQL)"),
                ("TEXT", "Implement rate limiting and security groups")
            ], "Configured ports: 22, 80, 443, 5432. Added rate limiting rules..."),
            ("Setup monitoring", [
                ("URL", "https://wiki.example.com/monitoring"),
                ("TEXT", "Install Prometheus + Grafana with default dashboards")
            ], "Prometheus + Grafana")
        ]),
        ("New Employee", "Employee onboarding process", [
            ("IT access setup", [
                ("URL", "https://it.example.com"),
                ("TEXT", "Required accounts: Email, Slack, Github, AWS, VPN, JIRA")
            ], "Created accounts for: Email, Slack, Github, AWS..."),
            ("HR documentation", [
                ("URL", "https://hr.example.com"),
                ("TEXT", "Complete I-9, W-4, Benefits enrollment, Direct deposit")
            ], "Forms pending"),
            ("Team introduction", [
                ("TEXT", "Schedule: Tech Lead, PM, Design Lead, Team standup")
            ], "Met with core team members...")
        ]),
        ("Release Process", "Software release checklist", [
            ("Run tests", [
                ("URL", "https://ci.example.com"),
                ("TEXT", "Run: Unit tests, Integration tests, Load tests, Security scan")
            ], "All integration tests passed..."),
            ("Update changelog", [
                ("TEXT", "Include: Features, Fixes, Breaking changes")
            ], "Done"),
            ("Deploy to staging", [
                ("URL", "https://deploy.example.com"),
                ("TEXT", "Verify: DB migrations, Config changes, Service health")
            ], "Staged v2.1.4")
        ]),
        ("Camping Trip Prep", "Essential camping preparation checklist", [
            ("Gear check", [
                ("URL", "https://rei.com/camping-essentials"),
                ("TEXT", "Essential gear: Tent, sleeping bags, pads, headlamps, stove")
            ], "Tent (3-season), sleeping bags..."),
            ("Food and water plan", [
                ("URL", "https://trailmeals.com"),
                ("TEXT", "Plan 2500 calories/person/day + emergency rations")
            ], "3 days food packed..."),
            ("Location logistics", [
                ("URL", "https://recreation.gov/camping"),
                ("TEXT", "Save offline: Maps, emergency contacts, ranger numbers")
            ], "Campsite #47 reserved...")
        ]),
        ("New House Setup", "First week move-in checklist", [
            ("Utilities setup", [
                ("URL", "https://utilities.movehelper.com"),
                ("TEXT", "Contact: Electric, Water, Gas, Internet, Waste")
            ], "Called: Electric (on), Water (scheduled)..."),
            ("Security check", [
                ("URL", "https://homesecurity.guide"),
                ("TEXT", "Check: Locks, smoke detectors, cameras, lighting")
            ], "Changed all locks..."),
            ("Deep clean", [
                ("TEXT", "Areas: Kitchen, bathrooms, HVAC, windows, floors")
            ], "All cabinets wiped...")
        ]),
        ("Home Organization", "Complete home organization system", [
            ("Kitchen optimization", [
                ("URL", "https://konmari.com/kitchen"),
                ("TEXT", "Zones: Cooking, Prep, Storage, Cleaning")
            ], "Implemented zones: cooking, prep..."),
            ("Closet systems", [
                ("URL", "https://closetmaid.com/design"),
                ("TEXT", "Sort: Season, Color, Type, Usage frequency")
            ], "Installed shelf organizers..."),
            ("Paper management", [
                ("URL", "https://paperless.guide"),
                ("TEXT", "System: Action, Archive, Scan, Shred")
            ], "Set up filing system...")
        ])
    ]
    
    created = []
    for title, desc, step_data in checklists_data:
        cl = create_checklist(title, desc)
        for step_text, refs, note in step_data:
            _, step = cl.add_step(step_text)
            for ref_type, ref_value in refs:
                step.add_reference(ref_value, ref_type)
        
        # Create instances with varying progress
        instances = [
            create_instance(cl.id, f"{title} - New", 
                          target_date=pendulum.now().add(days=7).to_date_string()),
            create_instance(cl.id, f"{title} - In Progress",
                          target_date=pendulum.now().add(days=3).to_date_string()),
            create_instance(cl.id, f"{title} - Almost Done",
                          target_date=pendulum.now().add(days=1).to_date_string())
        ]
        
        # Update progress for second and third instances
        step_list = L(steps(where=f"checklist_id = {cl.id}"))
        for i, (_, _, note) in enumerate(step_data):
            # Second instance: first step completed, second in progress
            if i == 0:
                instances[1].update_step_status(step_list[i].id, "Completed")
            elif i == 1:
                instances[1].update_step_status(step_list[i].id, "In Progress")
            instances[1].add_step_note(step_list[i].id, note)
            
            # Third instance: all but last step completed
            if i < len(step_data) - 1:
                instances[2].update_step_status(step_list[i].id, "Completed")
            else:
                instances[2].update_step_status(step_list[i].id, "In Progress")
            instances[2].add_step_note(step_list[i].id, note)
        
        for inst in instances[1:]:
            inst.update_status()
        
        created.append((cl, instances))
    
    return created

def clean_test_data():
    "Remove all test data from database"
    with DBConnection() as cur:
        # Get all checklists first
        cur.execute("SELECT id FROM checklists")
        checklist_ids = [r[0] for r in cur.fetchall()]
        
        # Process one at a time
        for cid in checklist_ids:
            try:
                # Delete instances first
                cur.execute(f"DELETE FROM instance_steps WHERE checklist_instance_id IN (SELECT id FROM checklist_instances WHERE checklist_id = {cid})")
                cur.execute(f"DELETE FROM checklist_instances WHERE checklist_id = {cid}")
                # Delete step references
                cur.execute(f"DELETE FROM step_references WHERE step_id IN (SELECT id FROM steps WHERE checklist_id = {cid})")
                # Delete steps
                cur.execute(f"DELETE FROM steps WHERE checklist_id = {cid}")
                # Finally delete checklist
                cur.execute(f"DELETE FROM checklists WHERE id = {cid}")
            except Exception as e:
                print(f"Error deleting checklist {cid}: {e}")
                
    print(f"Cleaned {len(checklist_ids)} checklists")
    return []


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







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


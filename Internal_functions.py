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



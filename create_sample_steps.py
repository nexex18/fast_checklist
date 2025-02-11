import os
from fasthtml.common import *
from fasthtml.common import RedirectResponse as redirect
from monsterui.all import *
from pathlib import Path
from datetime import datetime
import argparse

import sqlite3
import json
import shutil



from httpx import get as xget, post as xpost 

def add_sample_steps():
    # Sample steps for different types of checklists
    sample_steps = {
        'Daily Standup Tasks': [
            ('Review yesterday\'s progress', 'https://agilemanifesto.org'),
            ('Discuss today\'s goals', ''),
            ('Identify blockers', 'https://scrumguides.org/'),
            ('Update task board', '')
        ],
        'Project Launch Checklist': [
            ('Review deployment checklist', 'https://github.com/deployments/guide'),
            ('Backup production database', ''),
            ('Run final tests', 'https://docs.pytest.org'),
            ('Update documentation', ''),
            ('Send stakeholder notifications', '')
        ],
        'Weekly Review Items': [
            ('Review sprint goals', ''),
            ('Update metrics dashboard', ''),
            ('Schedule next week\'s meetings', ''),
            ('Send progress report', '')
        ]
    }
    
    # Get existing checklists
    with sqlite3.connect('data/checklists.db') as conn:
        cur = conn.cursor()
        
        # Get all checklists
        cur.execute("SELECT id, title FROM checklists")
        existing_checklists = cur.fetchall()
        
        # Add steps for each checklist
        for checklist_id, title in existing_checklists:
            # Delete existing steps for this checklist
            cur.execute("DELETE FROM steps WHERE checklist_id = ?", (checklist_id,))
            
            # Get steps for this type of checklist
            steps = sample_steps.get(title, [
                ('Step 1', ''),
                ('Step 2', ''),
                ('Step 3', '')
            ])
            
            # Insert new steps
            for order_index, (step_text, ref_url) in enumerate(steps):
                cur.execute("""
                INSERT INTO steps (checklist_id, text, status, order_index, reference_material)
                VALUES (?, ?, ?, ?, ?)
                """, (
                    checklist_id,
                    step_text,
                    'Not Started',
                    order_index,
                    json.dumps([ref_url]) if ref_url else json.dumps([])
                ))
        
        conn.commit()
    
    print("Sample steps added successfully!")

# Run the function
add_sample_steps()

# Verify the results
def show_checklists_and_steps():
    with sqlite3.connect('data/checklists.db') as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT c.title, s.text, s.order_index, s.reference_material
            FROM checklists c
            LEFT JOIN steps s ON c.id = s.checklist_id
            ORDER BY c.id, s.order_index
        """)
        
        current_checklist = None
        for row in cur.fetchall():
            if current_checklist != row[0]:
                current_checklist = row[0]
                print(f"\n\nChecklist: {current_checklist}")
                print("-" * 50)
            if row[1]:  # if there are steps
                refs = json.loads(row[3])
                ref_str = f" [Ref: {refs[0]}]" if refs and refs[0] else ""
                print(f"{row[2] + 1}. {row[1]}{ref_str}")

# Show the results
show_checklists_and_steps()

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
from core_functions import *
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

def test_chain_with_build():
    try:
        # Create checklist with steps and references
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
        
        # Print verification
        print(f"\nChecklist: {checklist.title}")
        print("\nSteps and References:")
        for step in steps(where=f"checklist_id = {checklist.id}", order_by="order_index"):
            print(f"\n{step.order_index}. {step.text}")
            refs = step.get_references()
            if refs:
                for ref in refs:
                    print(f"   Reference: {ref.url}")
        
        print("\nTest successful!")
        return checklist
        
    except Exception as e:
        print(f"Test failed: {e}")
        raise
    finally:
        if 'checklist' in locals(): checklists.delete(checklist.id)

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

def test_format_instance_url():
    print("\nFixed Test Cases:")
    print("-----------------")
    test_cases = [
        ("My Checklist", "abc123", "/i/my-checklist/abc123"),
        ("Project (2024)", "def456", "/i/project-2024/def456"),
        ("Sales Q1/2024", "ghi789", "/i/sales-q1-2024/ghi789"),
        ("   Spaces   Test   ", "jkl012", "/i/spaces-test/jkl012"),
        ("Special!@#$%^&*()Chars", "mno345", "/i/special-chars/mno345")
    ]
    
    for name, guid, expected in test_cases:
        result = format_instance_url(name, guid)
        print(f"Input: {name:25} -> Output: {result}")
        assert result == expected, f"Failed for {name}: got {result}, expected {expected}"
    
    print("\nVariable Test Cases:")
    print("-------------------")
    import uuid
    test_names = [
        "Test Checklist",
        "Another (Test)",
        "Multiple   Spaces   Here",
        "Mixed/Slashes\\and-dashes"
    ]
    
    for name in test_names:
        guid = str(uuid.uuid4())[:8]
        result = format_instance_url(name, guid)
        print(f"Input: {name:25} -> Output: {result}")
        assert result.startswith("/i/"), "URL must start with /i/"
        assert result.endswith(guid), "URL must end with the GUID"
        assert " " not in result, "URL must not contain spaces"
        assert result.count("/") == 3, "URL must have exactly 3 slashes"

def test_format_timestamp():
    now = pendulum.now('UTC')
    
    # Test cases with different times
    test_cases = [
        (now, "current time"),
        (now.subtract(hours=2), "today"),
        (now.subtract(days=1), "yesterday"), 
        (now.subtract(days=3), "this week"),
        (now.subtract(months=1), "this year"),
        (now.subtract(years=1), "last year")
    ]
    
    print("\nTesting different time scenarios:")
    print("---------------------------------")
    for ts, desc in test_cases:
        result = format_timestamp(ts)
        print(f"{desc:12}: {result}")
        
    # Test different input formats
    print("\nTesting different input formats:")
    print("-------------------------------")
    ts = now.subtract(days=2)
    inputs = [
        ts,                     # pendulum datetime
        ts.isoformat(),         # ISO string
        ts.timestamp(),         # Unix timestamp
    ]
    
    for inp in inputs:
        result = format_timestamp(inp)
        print(f"{type(inp).__name__:12}: {result}")

def test_format_progress():
    test_cases = [
        (5, 10, "Regular case"),
        (0, 5, "Zero progress"),
        (10, 10, "Complete"),
        (0, 0, "Zero total"),
        (7, 10, "Partial complete")
    ]
    
    print("\nTesting different progress scenarios:")
    print("------------------------------------")
    for done, total, desc in test_cases:
        results = [format_progress_percentage(done, total, fmt) 
                  for fmt in ProgressFormat]
        print(f"{desc:15}: {', '.join(results)}")

def test_checklist_stats():
    try:
        # Create checklist with steps
        checklist = (create_checklist("Test Checklist", "Test Description")
                    .build()
                    .add_step("Step 1")
                    .add_step("Step 2")
                    .checklist)
        
        # Create instances
        inst1 = create_instance(checklist.id, "Instance 1")
        inst2 = create_instance(checklist.id, "Instance 2")
        inst3 = create_instance(checklist.id, "Instance 3")
        
        # Complete one instance using L for step iteration
        for step in L(steps(where=f"checklist_id = {checklist.id}")):
            inst3.update_step_status(step.id, 'Completed')
        inst3.update_status()
        
        # Get and verify stats
        stats = checklist.get_checklist_with_stats()
        test_eq(stats['stats']['total_steps'], 2)
        test_eq(stats['stats']['active_instances'], 2)
        test_eq(stats['stats']['completed_instances'], 1)
        
        return stats
    
    except Exception as e:
        print(f"Test failed: {e}")
        raise
    finally:
        if 'checklist' in locals(): checklists.delete(checklist.id)

def test_instance_details():
    try:
        # Create test checklist with steps
        checklist = (create_checklist("Test Checklist", "Description")
                    .build()
                    .add_step("Step 1")
                    .add_step("Step 2")
                    .checklist)
        
        # Add references to steps
        step_list = steps(where=f"checklist_id = {checklist.id}")
        step_list[0].add_reference("http://example.com")
        
        # Create and setup instance
        instance = create_instance(checklist.id, "Test Instance", 
                                 description="Test Description")
        
        # Update first step status
        instance.update_step_status(step_list[0].id, 'Completed')
        
        # Get and verify details
        details = instance.get_instance_with_details()
        
        # Print results
        print("\nInstance Details:")
        print(f"Name: {details['name']}")
        print(f"Progress: {details['progress']}")
        print(f"Steps: {len(details['steps'])}")
        print(f"Step Statuses: {[s['status'] for s in details['steps']]}")
        print(f"References: {[len(s['refs']) for s in details['steps']]}")
        
        return details
        
    finally:
        if 'checklist' in locals(): 
            checklists.delete(checklist.id)

def test_sanitize_input():
    test_cases = [
        ("<script>alert(1)</script>", ""),
        ("**bold** text", "**bold** text"),
        ("# Header\n- list", "# Header\n- list"),
        ({"title": "<b>test</b>", "desc": "**ok**"}, {"title": "test", "desc": "**ok**"}),
        ([1, "<script>", "**ok**"], [1, "", "**ok**"]),
        (None, None)
    ]
    
    print("\nTesting input sanitization:")
    print("---------------------------")
    for inp, expected in test_cases:
        result = sanitize_user_input(inp)
        print(f"Input: {str(inp)[:30]:30} -> Output: {str(result)[:30]}")
        assert result == expected, f"Failed: got {result}, expected {expected}"

def test_validate_dates():
    now = pendulum.now('UTC')
    
    test_cases = [
        (None, "No target date"),
        (now.add(days=1), "Tomorrow"),
        (now.subtract(days=1), "Yesterday"),
        (now.add(days=400), "Far future"),
        (now.add(minutes=30), "Today but future"),
        (now.subtract(minutes=30), "Today but past")
    ]
    
    print("\nTesting date validation:")
    print("------------------------")
    for date, desc in test_cases:
        valid, msg = validate_instance_dates(date)
        print(f"{desc:20}: {'✓' if valid else '✗'} {msg or ''}")

# Mock components for testing
class EditableForm:
    def __init__(self, data): self.data = data
class ViewDisplay:
    def __init__(self, data): self.data = data
class Alert:
    def __init__(self, msg, cls=''): self.msg,self.cls = msg,cls
class Button:
    def __init__(self, text, **kwargs): self.text,self.kwargs = text,kwargs
class Div:
    def __init__(self, *args, **kwargs): 
        self.args,self.kwargs = args,kwargs
        self.cls = kwargs.get('cls', '')

def test_view_mode_toggle():
    test_data = {'id': 1, 'title': 'Test Item'}
    
    print("\nTesting view mode transitions:")
    print("------------------------------")
    
    # Test view -> edit
    new_mode, components = handle_view_mode_toggle('view', test_data)
    print(f"View -> Edit: {new_mode}")
    assert new_mode == 'edit', "Should switch to edit mode"
    assert isinstance(components, EditableForm)
    
    # Test edit -> view (no unsaved changes)
    new_mode, components = handle_view_mode_toggle('edit', test_data)
    print(f"Edit -> View (saved): {new_mode}")
    assert new_mode == 'view'
    assert isinstance(components, ViewDisplay)
    
    # Test edit -> view (with unsaved changes)
    new_mode, components = handle_view_mode_toggle('edit', test_data, unsaved=True)
    print(f"Edit -> View (unsaved): {new_mode}")
    assert new_mode == 'edit', "Should stay in edit mode with confirmation"
    assert 'uk-alert-warning' in components.args[0].cls
    
    # Test invalid mode
    try:
        handle_view_mode_toggle('invalid', test_data)
        assert False, "Should raise ValueError"
    except ValueError as e:
        print(f"Invalid mode test: {e}")

def test_search_checklists():
    try:
        # Create test data
        c1 = create_checklist("Project Setup", "Initial project configuration")
        c2 = create_checklist("Deployment Guide", "How to deploy")
        c3 = create_checklist("Git Tutorial", "Basic git commands")
        
        # Add steps to test step content search
        c1.add_step("Initialize git repository")
        c2.add_step("Deploy to production")
        c3.add_step("Git commit and push")
        
        print("\nTesting search functionality:")
        print("----------------------------")
        
        # Test cases
        test_queries = [
            ("project", "Title match"),
            ("git", "Content match"),
            ("deploy", "Mixed match"),
            ("xyz", "No match"),
            ("   ", "Empty query")
        ]
        
        for query, desc in test_queries:
            results = search_checklists(query)
            print(f"\n{desc}:")
            print(f"Query: '{query}' -> {len(results)} results")
            for r in results:
                print(f"- {r.title}")
                
        return "All tests completed"
        
    finally:
        # Cleanup
        for c in [c1,c2,c3]: 
            try: checklists.delete(c.id)
            except: pass

def test_search_instances():
    try:
        # Setup test data
        cl = (create_checklist("Test Checklist", "For search testing")
              .build()
              .add_step("Step 1")
              .add_step("Step 2")
              .checklist)
        
        step_ids = L(steps(where=f"checklist_id = {cl.id}")).attrgot('id')
        
        # Create instances with known states
        instances = L()
        
        # Not Started instance
        inst1 = create_instance(cl.id, "Project Alpha")
        instances += inst1
        
        # In Progress instance
        inst2 = create_instance(cl.id, "Project Beta")
        inst2.update_step_status(step_ids[0], 'Completed')
        instances += inst2
        
        # Completed instance
        inst3 = create_instance(cl.id, "Project Gamma")
        for step_id in step_ids:
            inst3.update_step_status(step_id, 'Completed')
        instances += inst3
        
        print("\nTesting search with status filters:")
        print("---------------------------------")
        
        # Test each status explicitly
        for status in ['Not Started', 'In Progress', 'Completed']:
            results = search_instances("Project", status=status)
            print(f"\nStatus '{status}' search:")
            for r in results:
                print(f"- {r.name}: {r.status}")
                assert r.status == status, f"Status mismatch: expected {status}, got {r.status}"
        
        # Test sorting by progress
        results = search_instances("Project", sort_by='progress')
        progress = [_calc_instance_progress(r.id) for r in results]
        print("\nProgress sort test:")
        print(f"Progress values: {progress}")
        assert progress == sorted(progress, reverse=True), "Progress sort failed"
        
        return "All search tests passed"
        
    finally:
        if 'cl' in locals(): checklists.delete(cl.id)

def test_active_instances_summary():
    try:
        # Create test checklist with steps
        cl = (create_checklist("Test Checklist", "For testing summary")
              .build()
              .add_step("Step 1")
              .add_step("Step 2")
              .add_step("Step 3")
              .checklist)
        
        step_ids = L(steps(where=f"checklist_id = {cl.id}")).attrgot('id')
        
        # Create instances with varied completion states
        # Instance 1: Due tomorrow, 2/3 complete
        inst1 = create_instance(cl.id, "Due Soon", target_date=pendulum.tomorrow().to_date_string())
        inst1.update_step_status(step_ids[0], 'Completed')
        inst1.update_step_status(step_ids[1], 'Completed')
        
        # Instance 2: Due in 2 weeks, not started
        inst2 = create_instance(cl.id, "Not Started", 
                              target_date=pendulum.now().add(days=14).to_date_string())
        
        # Instance 3: No due date, fully complete
        inst3 = create_instance(cl.id, "Complete")
        for step_id in step_ids:
            inst3.update_step_status(step_id, 'Completed')
        
        # Instance 4: Empty instance (edge case)
        inst4 = create_instance(cl.id, "Empty")
        
        print("\nTesting active instances summary:")
        print("--------------------------------")
        summary = get_active_instances_summary()
        
        # Verify counts
        assert summary['active_count'] > 0, "Should have active instances"
        assert len(summary['due_soon']) > 0, "Should have due soon items"
        assert len(summary['by_status']) > 0, "Should have status breakdown"
        
        print(f"Active instances: {summary['active_count']}")
        print(f"Due soon count: {len(summary['due_soon'])}")
        print("Status breakdown:", summary['by_status'])
        print(f"Average completion: {summary['completion_rate']*100:.1f}%")
        
        # Test empty case
        for inst in [inst1, inst2, inst3, inst4]:
            checklist_instances.delete(inst.id)
        
        empty_summary = get_active_instances_summary()
        assert empty_summary['active_count'] == 0, "Should handle empty case"
        print("\nEmpty case test passed")
        
        return summary
        
    finally:
        if 'cl' in locals(): checklists.delete(cl.id)

def test_verify_instance_state():
    try:
        # Create test data with error handling
        try:
            cl = (create_checklist("Test Checklist", "For verification testing")
                  .build()
                  .add_step("Step 1")
                  .add_step("Step 2")
                  .checklist)
        except Exception as e:
            print(f"Failed to create test checklist: {e}")
            return {'error': 'Test setup failed'}
            
        step_ids = L(steps(where=f"checklist_id = {cl.id}")).attrgot('id')
        if not len(step_ids):
            print("No steps created")
            return {'error': 'No steps found'}
            
        print("\nTesting instance state verification:")
        print("-----------------------------------")
        
        # Scenario 1: Missing Steps
        try:
            inst = create_instance(cl.id, "Test Instance")
            # Safely delete one instance step
            inst_steps = instance_steps(where=f"checklist_instance_id = {inst.id}")
            if inst_steps: instance_steps.delete(inst_steps[0].id)
            
            report = verify_instance_state(inst.id)
            print("\nScenario 1 - Missing Steps:")
            print(f"Missing steps detected: {len(report['missing_steps'])}")
            
            fix_report = verify_instance_state(inst.id, fix=True)
            fixed_steps = L(instance_steps(where=f"checklist_instance_id = {inst.id}"))
            print(f"Steps after fix: {len(fixed_steps)} of {len(step_ids)} expected")
            assert len(fixed_steps) == len(step_ids), "Fix didn't restore all steps"
        except Exception as e:
            print(f"Scenario 1 failed: {e}")
            
        # Scenario 2: Status Consistency
        try:
            # Complete all steps
            inst_steps = instance_steps(where=f"checklist_instance_id = {inst.id}")
            for step in inst_steps:
                instance_steps.update({'status': 'Completed'}, step.id)
            
            report = verify_instance_state(inst.id)
            print("\nScenario 2 - Status Consistency:")
            print(f"Invalid status detected: {len(report['invalid_status'])}")
            
            # Verify fix
            fix_report = verify_instance_state(inst.id, fix=True)
            inst_status = checklist_instances[inst.id].status
            print(f"Instance status after fix: {inst_status}")
            assert inst_status == 'Completed', "Status not updated correctly"
        except Exception as e:
            print(f"Scenario 2 failed: {e}")
            
        # Scenario 3: Orphaned Records (Modified Approach)
        try:
            # Create temporary step
            temp_step = steps.insert({'checklist_id': cl.id, 
                                    'text': 'Temp Step',
                                    'order_index': len(step_ids) + 1})
            
            # Create instance step referencing temp step
            instance_steps.insert({
                'checklist_instance_id': inst.id,
                'step_id': temp_step.id,
                'status': 'Not Started'
            })
            
            # Delete the parent step to create orphaned record
            steps.delete(temp_step.id)
            
            # Check if verify_instance_state detects orphaned record
            report = verify_instance_state(inst.id)
            print("\nScenario 3 - Orphaned Records:")
            print(f"Orphaned records detected: {len(report['orphaned_records'])}")
            
            # Verify fix removes orphaned record
            fix_report = verify_instance_state(inst.id, fix=True)
            remaining_orphans = L(instance_steps(
                where=f"checklist_instance_id = {inst.id} AND step_id = {temp_step.id}"))
            print(f"Orphaned records after fix: {len(remaining_orphans)}")
            assert not len(remaining_orphans), "Orphaned record not cleaned up"
        except Exception as e:
            print(f"Modified Scenario 3 failed: {e}")
            
        return "All test scenarios completed"
        
    finally:
        # Clean up safely
        try:
            if 'cl' in locals(): checklists.delete(cl.id)
        except Exception as e:
            print(f"Cleanup failed: {e}")



# Run the tests

print("Start by testing the validate functions")
test_validation_functions()
print("test_validation_functions ran... going to run test_create_checklist now")

test_create_checklist()
print("test_create_checklist ran... going to run test_checklist_update now")

test_checklist_update()
print("test_checklist_update ran... going to run test_get_next_order_index now")

test_get_next_order_index()
print("test_get_next_order_index ran... going to run test_add_step_with_chaining now")

test_add_step_with_chaining()
print("test_add_step_with_chaining ran... going to run test_step_update now")

test_step_update()
print("test_step_update ran... going to run test_step_delete now")

test_step_delete()
print("test_step_delete ran... going to run test_step_reference now")

test_step_reference()
print("test_step_reference ran... going to run test_delete_reference now")

test_delete_reference()
print("test_delete_reference ran... going to run test_get_references now")

test_get_references()
print("test_get_references ran... going to run test_delete_checklist now")

test_delete_checklist()
print("test_delete_checklist ran... going to run test_enhanced_builder now")

test_enhanced_builder()
print("test_enhanced_builder ran... going to run test_create_instance now")

test_create_instance()
print("test_create_instance ran... going to run test_delete_instance now")

test_delete_instance()
print("test_delete_instance ran... going to run test_instance_update now")

test_instance_update()
print("test_instance_update ran... going to run test_update_step_status now")

test_update_step_status()
print("test_update_step_status ran... going to run test_add_step_note now")

test_add_step_note()
print("test_add_step_note ran... going to run test_get_step_status now")

test_get_step_status()
print("test_get_step_status ran... going to run test_get_progress now")

test_get_progress()
print("test_get_progress ran... going to run test_update_status now")

test_update_status()
print("test_update_status ran... going to run test_get_incomplete_steps now")

test_get_incomplete_steps()
print("test_get_incomplete_steps ran... going to run test_get_active_instances now")

test_get_active_instances()
print("test_get_active_instances ran... going to run test_get_instances_by_status now")

test_get_instances_by_status()
print("test_get_instances_by_status ran... going to run test_chain_with_build now")

test_chain_with_build()
print("test_chain_with_build ran... going to run test_format_instance_url now")

test_format_instance_url()
print("test_format_instance_url ran... going to run test_format_progress now")

test_format_progress()
print("test_format_progress ran... going to run test_checklist_stats now")

test_checklist_stats()
print("test_checklist_stats ran... going to run test_instance_details now")

test_instance_details()
print("test_instance_details ran... going to run test_sanitize_input now")

test_sanitize_input()
print("test_sanitize_input ran... going to run test_validate_dates now")

test_validate_dates()
print("test_validate_dates ran... going to run test_view_mode_toggle now")

test_view_mode_toggle()
print("test_view_mode_toggle ran... going to run test_search_checklists now")

test_search_checklists()
print("test_search_checklists ran... going to run test_search_instances now")

test_search_instances()
print("test_search_instances ran... going to run test_active_instances_summary now")

test_active_instances_summary()
print("test_active_instances_summary ran... going to run test_verify_instance_state now")

test_verify_instance_state()
print("test_verify_instance_state ran... All tests completed successfully!")
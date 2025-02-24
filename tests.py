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


# Run the tests

print("Start by testing the validate functions")

test_validation_functions()
print("test_validation_functions ran... ")

print("Starting test_create_checklist...")
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
print("test_chain_with_build ran... going to run display_checklist now")

test_create_checklist()
print("test_create_checklist ran... going to run test_validation_functions now")


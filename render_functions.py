from httpx import get as xget, post as xpost
import os
from fasthtml.common import *
from fasthtml.common import RedirectResponse as redirect
from monsterui.all import *
from datetime import datetime
import sqlite3
from time import sleep
from fastcore.basics import AttrDict, patch

# Import from main or core_functions only what you absolutely need
from main import checklists, steps, reference_types, step_references, checklist_instances, instance_steps
from core_functions import create_checklist, Checklist, Step, StepReference, Instance

# Rest of your file remains the same

# Import Button directly from monsterui.all
from monsterui.all import (Button as MonsterButton, UkIcon, DivLAligned, Card, DivVStacked, 
                           DivRAligned, TextPresets, DivFullySpaced, ButtonT, NavBar, ContainerT)
from fasthtml.components import (Div, H3, P, Form, H4, Button, Hidden, Container, Section, 
                                H2, A, Script, Option)

def render_navbar():
    """Main navigation bar for the application"""
    return NavBar(
        A("Dashboard", href="/"),
        A("Checklists", href="/checklists"),
        A("Instances", href="/instances"),
        brand=DivLAligned(UkIcon("check-square", cls="mr-2"), H3("Checklist Manager")),
        cls="mb-6"
    )

def render_page_title(title, subtitle=None):
    """Renders a consistent page title with optional subtitle"""
    if subtitle:
        return DivVStacked(
            H2(title),
            P(subtitle, cls=TextPresets.muted_sm),
            cls="mb-6"
        )
    return DivVStacked(
        H2(title),
        cls="mb-6"
    )

def render_action_button(text, icon=None, button_type="uk-button-primary", **kwargs):
    """Renders a standardized action button with optional icon"""
    if icon:
        return MonsterButton(
            DivLAligned(UkIcon(icon, cls="mr-2"), text),
            cls=button_type,
            **kwargs
        )
    return MonsterButton(text, cls=button_type, **kwargs)

def render_checklist_header_view(checklist):
    """Renders the checklist header in view mode"""
    return Card(
        DivVStacked(
            H3(checklist.title),
            P(checklist.description, cls=TextPresets.muted_sm),
            P(checklist.description_long or "No detailed description provided."),
            cls="space-y-2"
        ),
        DivRAligned(
            render_action_button(
                "Edit", "pencil", 
                hx_get=f"/checklists/{checklist.id}/edit",
                hx_target="checklist-detail-container"
            )
        ),
        id="checklist-header",
        cls="mb-4 p-6"
    )

def render_checklist_header_edit(checklist):
    """Renders the checklist header in edit mode"""
    return Card(
        Form(
            LabelInput("Title", id="title", value=checklist.title),
            LabelTextArea("Description", id="description", value=checklist.description),
            LabelTextArea("Long Description", id="description_long", value=checklist.description_long or ""),
            DivRAligned(
                render_action_button(
                    "Cancel", "x", ButtonT.ghost,
                    hx_get=f"/checklists/{checklist.id}",
                    hx_target="checklist-detail-container"
                ),
                render_action_button(
                    "Save", "save",
                    type="submit"
                ),
                cls="space-x-4"
            ),
            hx_put=f"/checklists/{checklist.id}",
            hx_target="checklist-detail-container",
            cls="space-y-4"
        ),
        id="checklist-header-edit",
        cls="mb-4 p-6"
    )

def render_steps_header(checklist_id):
    """Renders the header for the steps section with add button"""
    return Div(
        DivFullySpaced(
            H3("Steps"),
            render_action_button(
                "Add Step", "plus-circle",
                hx_get=f"/checklists/{checklist_id}/steps/new",
                hx_target="new-step-form-container"
            )
        ),
        P("Drag and drop steps to reorder them.", cls=TextPresets.muted_sm),
        cls="mb-4"
    )

def render_reference_item(reference, reference_type_name=None):
    """Renders a single reference with its type as a card"""
    ref_id = f"reference-{reference.id}"
    
    if reference_type_name is None:
        # Try to determine type based on reference_type_id
        ref_type = next((rt for rt in reference_types() if rt.id == reference.reference_type_id), None)
        reference_type_name = ref_type.name if ref_type else "URL"
    
    # Set icon based on reference type
    icon_map = {
        "Documentation": "file-text",
        "API": "server",
        "Guide": "book-open",
        "Example": "code",
        "URL": "link",
        "TEXT": "file-text"
    }
    icon = icon_map.get(reference_type_name, "link")
    
    # For TEXT references, display differently than URLs
    is_url = reference_type_name == "URL"
    
    # Get domain from URL for display (only for actual URLs)
    url_domain = ""
    if is_url:
        try:
            from urllib.parse import urlparse
            url_domain = urlparse(reference.url).netloc
        except:
            pass
    
    content = Div(
        A(reference.url, href=reference.url if is_url else "#", 
          target="_blank" if is_url else None, 
          cls="font-medium hover:underline"),
        P(url_domain if is_url else "", cls=TextPresets.muted_sm),
        cls="flex-1"
    )
    
    # For TEXT references, display the content differently
    if not is_url:
        content = Div(
            P(reference.url, cls="font-medium"),
            cls="flex-1"
        )
    
    return Card(
        DivLAligned(
            UkIcon(icon, cls="mr-2 text-primary"),
            content
        ),
        DivFullySpaced(
            Label(reference_type_name, cls="p-1 text-xs bg-gray-100 rounded"),
            Button(UkIcon("trash-2"), 
                  cls=(ButtonT.ghost, "p-1", "text-red-500"),
                  hx_delete=f"/references/{reference.id}",
                  hx_target=ref_id,
                  hx_swap="outerHTML")
        ),
        id=ref_id,
        cls="p-3 mb-2"
    )

def render_step_item(step, references=None, is_sortable=True):
    """Renders a single step item in view mode with its references"""
    if references is None:
        references = []
    
    step_id = f"step-{step.id}"
    
    # References section
    references_section = Div(id=f"{step_id}-references")
    if references:
        references_section = Div(
            H4("References", cls=(TextT.sm, TextT.medium, "mb-2")),
            *[render_reference_item(ref) for ref in references],
            id=f"{step_id}-references",
            cls="mt-3 space-y-2"
        )
    
    handle = ""
    if is_sortable:
        handle = Div(
            UkIcon("grip-vertical", cls="text-gray-400 cursor-move"),
            cls="step-handle p-2"
        )
    
    return Card(
        DivFullySpaced(
            DivLAligned(
                handle,
                P(step.text, cls="flex-1")
            ),
            DivHStacked(
                Button(UkIcon("edit-3"), 
                      hx_get=f"/steps/{step.id}/edit",
                      hx_target=step_id,
                      cls="uk-button-ghost p-1"),
                Button(UkIcon("trash-2"), 
                      hx_delete=f"/steps/{step.id}",
                      hx_confirm="Are you sure you want to delete this step?",
                      hx_target=step_id,
                      hx_swap="outerHTML",
                      cls="uk-button-ghost p-1 text-red-500"),
                cls="space-x-2"
            )
        ),
        references_section,
        DivRAligned(
            render_action_button(
                "Add Reference", "link", "uk-button-secondary",
                hx_get=f"/steps/{step.id}/references/new",
                hx_target=f"{step_id}-reference-form"
            )
        ),
        Div(id=f"{step_id}-reference-form"),
        id=step_id,
        cls="mb-4 p-4",
        data_step_id=step.id,
        data_order=step.order_index
    )

def render_step_item_edit(step):
    """Renders a single step item in edit mode"""
    step_id = f"step-{step.id}"
    
    return Card(
        Form(
            LabelTextArea("Step Text", id="text", value=step.text),
            Hidden(id="id", value=step.id),
            Hidden(id="checklist_id", value=step.checklist_id),
            Hidden(id="order_index", value=step.order_index),
            DivRAligned(
                render_action_button(
                    "Cancel", "x", "uk-button-default",
                    hx_get=f"/steps/{step.id}",
                    hx_target=step_id
                ),
                render_action_button(
                    "Save", "save",
                    type="submit"
                ),
                cls="space-x-4"
            ),
            hx_put=f"/steps/{step.id}",
            hx_target=step_id,
            cls="space-y-4"
        ),
        id=step_id,
        cls="mb-4 p-4"
    )

def render_new_step_form(checklist_id):
    """Renders the form for creating a new step"""
    return Card(
        Form(
            LabelTextArea("Step Text", id="text", placeholder="Enter step details..."),
            Hidden(id="checklist_id", value=checklist_id),
            DivRAligned(
                render_action_button(
                    "Cancel", "x", "uk-button-default",
                    hx_get="/empty",
                    hx_target="new-step-form-container"
                ),
                render_action_button(
                    "Add Step", "plus",
                    type="submit"
                ),
                cls="space-x-4"
            ),
            hx_post=f"/checklists/{checklist_id}/steps",
            hx_target="steps-list",
            hx_swap="beforeend",
            hx_on_after_request="this.reset(); document.getElementById('new-step-form-container').innerHTML = '';",
            cls="space-y-4"
        ),
        id="new-step-form",
        cls="mb-4 p-4"
    )

def render_steps_list(steps, checklist_id, get_references_fn=None):
    """Renders the full list of sortable steps with references"""
    if not steps:
        return Div(
            P("No steps have been added yet.", cls=TextPresets.muted_sm),
            cls="p-4 border rounded"
        )
    
    step_items = []
    for step in steps:
        references = []
        if get_references_fn:
            references = get_references_fn(step.id)
        step_items.append(render_step_item(step, references))
    
    # Add script for SortableJS to handle drag-and-drop
    sortable_script = Script("""
    document.addEventListener('DOMContentLoaded', function() {
        new Sortable(document.getElementById('steps-list'), {
            handle: '.step-handle',
            animation: 150,
            onEnd: function(evt) {
                const steps = Array.from(evt.to.children).map((el, index) => {
                    return {
                        id: el.dataset.stepId,
                        order: index + 1
                    };
                });
                
                // Send the updated order to the server
                htmx.ajax('POST', '/steps/reorder', {
                    target: '#steps-list',
                    swap: 'none',
                    values: {
                        steps: JSON.stringify(steps),
                        checklist_id: '""" + str(checklist_id) + """'
                    }
                });
            }
        });
    });
    """, type="text/javascript")
    
    return Div(
        Div(
            *step_items,
            id="steps-list",
            cls="space-y-4"
        ),
        sortable_script
    )

def render_reference_type_badge(name, is_selected=False, on_click=None):
    """Renders a selectable badge for reference types"""
    cls = "p-2 rounded cursor-pointer border text-sm mr-2 mb-2"
    if is_selected:
        cls += " bg-primary text-white"
    else:
        cls += " bg-white hover:bg-gray-100"
    
    return Div(
        name,
        cls=cls,
        id=f"ref-type-{name.lower().replace(' ', '-')}",
        hx_get=on_click if on_click else None
    )

def render_new_reference_form(step_id, reference_types):
    """Renders an enhanced form for adding a new reference to a step"""
    # Group reference types for better UI
    common_types = [rt for rt in reference_types if rt.name in ["Documentation", "API", "Guide", "Example"]]
    other_types = [rt for rt in reference_types if rt.name not in ["Documentation", "API", "Guide", "Example"]]
    
    return Card(
        Form(
            H4("Add Reference", cls="mb-4"),
            
            # URL input field
            LabelInput("URL", id="url", placeholder="https://example.com"),
            
            # Reference type selection as badges
            Div(
                P("Reference Type", cls=TextPresets.bold_sm),
                Div(
                    *[render_reference_type_badge(
                        rt.name, 
                        False, 
                        f"#ref-type-select?id={rt.id}"
                    ) for rt in common_types],
                    cls="flex flex-wrap mt-2"
                ),
                cls="mb-4"
            ),
            
            # Hidden reference type select for non-JS fallback and to store the value
            Hidden(id="reference_type_id", value=common_types[0].id if common_types else "1"),
            Hidden(id="step_id", value=step_id),
            
            # Additional reference types in a dropdown if there are many
            (LabelSelect(
                *[Option(rt.name, value=rt.id) for rt in other_types],
                label="Other Types",
                id="other_reference_type_id"
            ) if other_types else ""),
            
            DivRAligned(
                render_action_button(
                    "Cancel", "x", "uk-button-default",
                    hx_get="/empty",
                    hx_target=f"step-{step_id}-reference-form"
                ),
                render_action_button(
                    "Add Reference", "plus",
                    type="submit"
                ),
                cls="space-x-4"
            ),
            hx_post=f"/steps/{step_id}/references",
            hx_target=f"step-{step_id}-references",
            hx_swap="beforeend",
            hx_on_after_request="this.reset(); document.getElementById('step-" + str(step_id) + "-reference-form').innerHTML = '';",
            cls="space-y-4"
        ),
        # Script to handle reference type badge selection
        Script("""
        document.addEventListener('click', function(e) {
            if (e.target.closest('[id^="ref-type-"]')) {
                const badge = e.target.closest('[id^="ref-type-"]');
                const typeId = badge.id.replace('ref-type-', '');
                
                // Get the URL parameter
                const url = new URL(badge.getAttribute('hx-get'), window.location.origin);
                const typeIdParam = url.searchParams.get('id');
                
                // Update the hidden input
                document.querySelector('input[name="reference_type_id"]').value = typeIdParam;
                
                // Update visual state of badges
                document.querySelectorAll('[id^="ref-type-"]').forEach(b => {
                    b.classList.remove('bg-primary', 'text-white');
                    b.classList.add('bg-white');
                });
                badge.classList.add('bg-primary', 'text-white');
                badge.classList.remove('bg-white');
                
                // Prevent the HTMX request
                e.preventDefault();
            }
        });
        """, type="text/javascript"),
        id=f"step-{step_id}-reference-form",
        cls="mt-4 p-4 border rounded"
    )

def render_instances_header(checklist_id):
    """Renders the header for the instances section"""
    return DivFullySpaced(
        H3("Instances"),
        render_action_button(
            "Create Instance", "play-circle",
            hx_get=f"/instances/new/{checklist_id}",
            hx_push_url="true"
        ),
        cls="mb-4"
    )

def render_instance_item(instance):
    """Renders a single instance list item with progress"""
    # Calculate progress (assuming this returns percentage and counts)
    progress = instance.get_progress() if hasattr(instance, 'get_progress') else {'percentage': 0}
    percentage = progress.get('percentage', 0)
    
    # Format URL for the instance
    instance_url = f"/i/{instance.id}"  # Simplified for example
    if hasattr(instance, 'format_instance_url'):
        instance_url = format_instance_url(instance.name, str(instance.id))
    
    status_classes = {
        'Not Started': 'bg-gray-500',
        'In Progress': 'bg-blue-500',
        'Completed': 'bg-green-500'
    }
    status_class = status_classes.get(instance.status, 'bg-gray-500')
    
    return Card(
        DivFullySpaced(
            DivLAligned(
                Div(cls=f"w-3 h-3 rounded-full {status_class}"),
                H4(instance.name)
            ),
            DivLAligned(
                P(f"Created: {instance.created_at}", cls=TextPresets.muted_sm),
                P(f"Status: {instance.status}", cls=TextPresets.muted_sm),
                cls="space-x-4"
            )
        ),
        # Progress bar
        Div(
            Div(cls=f"h-2 {status_class} rounded", style=f"width:{percentage}%"),
            cls="w-full bg-gray-200 rounded h-2 mt-2"
        ),
        P(f"{int(percentage)}% complete", cls=TextPresets.muted_sm),
        # Target date if set
        instance.target_date and P(f"Target date: {instance.target_date}", cls=TextPresets.muted_sm),
        DivRAligned(
            render_action_button(
                "View", "eye",
                hx_get=instance_url,
                hx_push_url="true"
            )
        ),
        cls="uk-card-hover mb-3 p-4"
    )

def render_instances_list(instances):
    """Renders the list of instances for a checklist"""
    if not instances:
        return Div(
            P("No instances have been created yet.", cls=TextPresets.muted_sm),
            cls="p-4 border rounded"
        )
    
    return Div(
        *[render_instance_item(instance) for instance in instances],
        id="instances-list",
        cls="space-y-4"
    )

def render_checklist_edit_page(checklist, steps, instances, reference_types=None, get_references_fn=None):
    """Renders the complete checklist edit page"""
    # Default empty list if no reference types provided
    if reference_types is None:
        reference_types = []
        
    return Container(
        # Navbar
        render_navbar(),
        
        # Page title
        render_page_title(f"Edit Checklist: {checklist.title}"),
        
        # Checklist header section
        Div(
            render_checklist_header_view(checklist),
            id="checklist-detail-container"
        ),
        
        # Steps section
        Section(
            render_steps_header(checklist.id),
            Div(id="new-step-form-container"),
            render_steps_list(steps, checklist.id, get_references_fn),
            cls="mt-8"
        ),
        
        # Instances section
        # Section(
        #     render_instances_header(checklist.id),
        #     render_instances_list(instances),
        #     cls="mt-8"
        # ),
        
        # HTMX/Sortable script dependencies
        Script("""
        // Helper function to initialize all sortable elements
        function initSortables() {
            if (typeof Sortable !== 'undefined') {
                const sortableLists = document.querySelectorAll('.sortable-list');
                sortableLists.forEach(list => {
                    if (!list.sortableInstance) {
                        list.sortableInstance = new Sortable(list, {
                            handle: '.step-handle',
                            animation: 150,
                            onEnd: function(evt) {
                                // Handle reordering logic here
                            }
                        });
                    }
                });
            }
        }
        
        // Initialize sortables on page load
        document.addEventListener('DOMContentLoaded', initSortables);
        
        // Initialize sortables after any HTMX content swap
        document.body.addEventListener('htmx:afterSwap', initSortables);
        """, type="text/javascript"),
        
        cls=(ContainerT.xl, "space-y-4")
    )
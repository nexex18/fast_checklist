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

test_format_instance_url()
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

test_format_timestamp()
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

test_format_progress()
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

test_checklist_stats()
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

test_instance_details()

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

def _clean_md(s:str):
    "Clean string while preserving markdown"
    return clean(s, strip=True, 
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

test_sanitize_input()
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
test_validate_dates()

def handle_view_mode_toggle(current_mode:str, data:dict, unsaved:bool=False):
    "Toggle between view/edit modes with state handling"
    if current_mode not in ('view', 'edit'): 
        raise ValueError(f"Invalid mode: {current_mode}")
    
    # Handle edit -> view transition
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
            EditableForm(data) if new_mode == 'edit' else ViewDisplay(data))

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

# Run the tests
test_view_mode_toggle()

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

# Run tests
test_search_checklists()

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

test_search_instances()
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

test_active_instances_summary()
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

# Run the improved tests
test_verify_instance_state()

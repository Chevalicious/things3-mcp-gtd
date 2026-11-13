import things

from .url_scheme import show


def format_todo(todo: dict, include_details: bool = False) -> str:
    """Format a task with enough information to identify and file it."""
    fields = [f"Title: {todo['title']}", f"UUID: {todo['uuid']}"]
    if include_details:
        fields.append(f"Type: {todo['type']}")
    for key, label in (
        ("status", "Status"),
        ("start", "List"),
        ("start_date", "Start Date"),
        ("next_instance_start_date", "Next Occurrence"),
        ("deadline", "Deadline"),
    ):
        if todo.get(key):
            fields.append(f"{label}: {todo[key]}")

    for key, label in (
        ("project", "Project"),
        ("heading", "Heading"),
        ("area", "Area"),
    ):
        destination_id = todo.get(key)
        title = todo.get(f"{key}_title")
        if key == "heading" and destination_id:
            destination = (
                f"{title} (ID: {destination_id})" if title else f"ID: {destination_id}"
            )
        else:
            destination = title or destination_id
        if destination:
            fields.append(f"{label}: {destination}")

    if not include_details:
        return " · ".join(fields)

    for key, label in (
        ("stop_date", "Completed"),
        ("reminder_time", "Reminder"),
        ("notes", "Notes"),
    ):
        if todo.get(key):
            fields.append(f"{label}: {todo[key]}")
    if todo.get("tags"):
        fields.append(f"Tags: {', '.join(todo['tags'])}")

    checklist = todo.get("checklist")
    if checklist is True or checklist == 1:
        checklist = things.checklist_items(todo["uuid"])
    if isinstance(checklist, list):
        fields.append("Checklist:")
        for item in checklist:
            status = "✓" if item["status"] == "completed" else "□"
            fields.append(f"  {status} {item['title']}")

    if todo["type"] == "to-do":
        fields.append(f"[Open in Things]({show(id=todo['uuid'])})")

    return "\n".join(fields)


def format_project(project: dict, include_items: bool = False) -> str:
    """Helper function to format a single project."""
    project_text = f"Title: {project['title']}\nUUID: {project['uuid']}"

    if area := project.get("area_title") or project.get("area"):
        project_text += f"\nArea: {area}"

    if include_items:
        items = things.tasks(project=project["uuid"])
        headings = [item for item in items if item.get("type") == "heading"]
        if headings:
            project_text += "\n\nHeadings:"
            for heading in headings:
                project_text += f"\n- {heading['title']} (ID: `{heading['uuid']}`)"
        todos = [item for item in items if item.get("type") == "to-do"]
        if todos:
            project_text += "\n\nTasks:"
            for todo in todos:
                project_text += f"\n- {todo['title']}"

    return project_text


def format_area(area: dict, include_items: bool = False) -> str:
    """Helper function to format a single area."""
    area_text = f"Title: {area['title']}\nUUID: {area['uuid']}"

    if include_items:
        projects = things.projects(area=area["uuid"])
        if projects:
            area_text += "\n\nProjects:"
            for project in projects:
                area_text += f"\n- {project['title']}"

        todos = things.todos(area=area["uuid"])
        if todos:
            area_text += "\n\nTasks:"
            for todo in todos:
                area_text += f"\n- {todo['title']}"

    return area_text


def format_tag(tag: dict, include_items: bool = False) -> str:
    """Helper function to format a single tag."""
    tag_text = f"Title: {tag['title']}\nUUID: {tag['uuid']}"

    if tag.get("shortcut"):
        tag_text += f"\nShortcut: {tag['shortcut']}"

    if include_items:
        todos = things.todos(tag=tag["title"])
        if todos:
            tag_text += "\n\nTagged Items:"
            for todo in todos:
                tag_text += f"\n- {todo['title']}"

    return tag_text

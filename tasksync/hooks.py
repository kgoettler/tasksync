import json
import os

from tasksync.models import TaskwarriorTask
from todoist_api_python.api import TodoistAPI

def on_add(task_json_input) -> tuple[str, str]:
    # Read input
    task = TaskwarriorTask.from_taskwarrior(json.loads(task_json_input))

    # Connect to API    
    api = TodoistAPI(os.environ['TODOIST_API_KEY'])

    # If task has a Todoist id, attempt to update it
    feedback = ''
    res = api.add_task(**task.to_todoist_api_kwargs())
    task.todoist = res.id
    return (task.to_json(), feedback)


def on_modify(task_json_input, task_json_output) -> tuple[str, str]:
    # Read inputs
    task_input = TaskwarriorTask.from_taskwarrior(json.loads(task_json_input))
    task_output = TaskwarriorTask.from_taskwarrior(json.loads(task_json_output))

    # Connect to API    
    api = TodoistAPI(os.environ['TODOIST_API_KEY'])

    # If task has a Todoist id, attempt to update it
    feedback = ''
    if task_output.todoist is not None:
        #todoist_task = api.get_task(task_id=str(task.todoist))
        res = api.update_task(**task_output.to_todoist_api_kwargs())
    else:
        kwargs = task_output.to_todoist_api_kwargs()
        res = api.add_task(**kwargs)
        task_output.todoist = res.id

    return (task_output.to_json(), feedback)

from __future__ import annotations

from enum import Enum
from typing import TypedDict
from zoneinfo import ZoneInfo
import os
import subprocess
import uuid

from tasksync.models import TasksyncDatetime
from tasksync.taskwarrior.models import (
    TaskwarriorStatus,
    TaskwarriorTask
)
from tasksync.todoist.api import TodoistSyncDataStore
from tasksync.todoist.models import TodoistSyncDue

TODOIST_DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'

def add_item(task: TaskwarriorTask, store: TodoistSyncDataStore) -> list:
    ops = []
    data = {
        'type': 'item_add',
        'temp_id': str(task.uuid),
        'uuid': str(uuid.uuid4()),
        'args': {
            'content': task.description,
        }
    }
    if task.project:
        if project := store.find('projects', name=task.project):
            data['args']['project_id'] = project['id']
        else:
            temp_id = str(uuid.uuid4())
            ops.extend(create_project(name=task.project, temp_id=temp_id))
            data['args']['project_id'] = temp_id
    if task.due:
        data['args']['due'] = date_from_taskwarrior(task.due, task.timezone) # type: ignore
    if task.priority:
        data['args']['priority'] = task.priority.value + 1
    if len(task.tags) > 0:
        data['args']['labels'] = task.tags
    ops.append(data)
    return ops

def update_item(task_old: TaskwarriorTask, task_new: TaskwarriorTask, store: TodoistSyncDataStore) -> list:
    ops = []
    args = {}

    # Description
    if task_old.description != task_new.description:
        args['content'] = task_new.description

    # Due date
    if _check_update(task_old, task_new, 'due'):
        args['due'] = date_from_taskwarrior(task_new.due, task_new.timezone)  # type: ignore
    elif _check_remove(task_old, task_new, 'due'):
        args['due'] = None

    # Priority
    if _check_update(task_old, task_new, 'priority'):
        args['priority'] = task_new.priority.value + 1 # type: ignore
    elif _check_remove(task_old, task_new, 'priority'):
        args['priority'] = 1

    # Labels
    if _check_update(task_old, task_new, 'tags'):
        args['labels'] = task_new.tags

    # Build payload
    if len(args) > 0:
        data = {
            'type': 'item_update',
            'uuid': str(uuid.uuid4()),
            'args': {
                'id': str(task_new.todoist),
                **args,
            }
        }
        ops.append(data)
    return ops

def move_item(task_old: TaskwarriorTask, task_new: TaskwarriorTask, store: TodoistSyncDataStore) -> list:
    ops = []
    data = {
        'type': 'item_move',
        'uuid': str(uuid.uuid4()),
        'args': {
            'id': str(task_new.todoist),
        }
    }

    # Project
    project_id = None
    # (0, 1) or (1, 1)
    if task_new.project is not None:
        if project := store.find('projects', name=task_new.project):
            project_id = project['id']
            if task_old.project != task_new.project:
                data['args']['project_id'] = project_id
        else:
            # Project does not exist -- we need to create it
            # Use temporary uuid so we can identify it in successive calls, if needed
            project_id = str(uuid.uuid4())
            ops.extend(create_project(name=task_new.project, temp_id=project_id)) # type: ignore
            data['args']['project_id'] = project_id
    else:
        if project := store.find('projects', name='Inbox'):
            project_id = project['id']
            data['args']['project_id'] = project_id
        else:
            raise RuntimeError(
                'Attempting to move task to Inbox, but Inbox project not found in data store!'
            )

    # Now do the same thing for the section 
    if task_new.section is not None:
        # Section was updated
        if section := store.find('sections', name=task_new.section, project_id=project_id):
            # if it exists in this project, supply section_id as argument
            # instead of project_id
            section_id = section['id']
            data['args']['section_id'] = section['id']
            if 'project_id' in data['args']:
                del data['args']['project_id']
        else:
            # Section does not exist -- we need to create it
            section_id = str(uuid.uuid4())
            ops += create_section(name=task_new.section, temp_id=section_id, project_id=project_id) # type: ignore
            data['args']['section_id'] = section_id
    elif task_old.section is not None:
        # From API docs:
        # > to move an item from a section to no section, just use the
        # > project_id parameter, with the project it currently belongs to as a
        # > value.
        data['args']['project_id'] = project_id
    if len(data['args']) > 1:
        ops.append(data)
    return ops

def delete_item(task_old: TaskwarriorTask, task_new: TaskwarriorTask, store: TodoistSyncDataStore) -> list:
    ops = []
    if task_old.status != TaskwarriorStatus.DELETED and task_new.status == TaskwarriorStatus.DELETED:
        data = {
            'type': 'item_delete',
            'uuid': str(uuid.uuid4()),
            'args': {
                'id': str(task_new.todoist),
            }
        }
        ops.append(data)
    return ops

def complete_item(task_old: TaskwarriorTask, task_new: TaskwarriorTask, store: TodoistSyncDataStore) -> list:
    ops = []
    if task_old.status != TaskwarriorStatus.COMPLETED and task_new.status == TaskwarriorStatus.COMPLETED:
        data = {
            'type': 'item_complete',
            'uuid': str(uuid.uuid4()),
            'args': {
                'id': str(task_new.todoist),
            }
        }
        if task_new.end is not None:
            data['args']['date_completed'] = task_new.end.strftime(TODOIST_DATETIME_FORMAT)
        ops.append(data)
    return ops

def uncomplete_item(task_old: TaskwarriorTask, task_new: TaskwarriorTask, store: TodoistSyncDataStore) -> list:
    ops = []
    if task_old.status == TaskwarriorStatus.COMPLETED and task_new.status != TaskwarriorStatus.COMPLETED:
        data = {
            'type': 'item_uncomplete',
            'uuid': str(uuid.uuid4()),
            'args': {
                'id': str(task_new.todoist),
            }
        }
        ops.append(data)
    return ops

def create_project(name : str,
                   temp_id : str | None = None,
                   color : str | None = None,
                   parent_id : str | None = None,
                   child_order : int | None = None,
                   is_favorite : bool | None = None,
                   view_style : str | None = None
                   ) -> list:
    ops = []
    data = {
        'type': 'project_add',
        'uuid': str(uuid.uuid4()),
        'args': {
            'name': name,
        }
    }
    if temp_id:
        data['temp_id'] = temp_id
    if color:
        data['args']['color'] = color
    if parent_id:
        data['args']['parent_id'] = parent_id
    if child_order is not None:
        data['args']['child_order'] = child_order
    if is_favorite is not None:
        data['args']['is_favorite'] = is_favorite
    if view_style is not None:
        data['args']['view_style'] = view_style
    ops.append(data) 
    return ops

def create_section(name : str,
                   temp_id : str,
                   project_id : str,
                   section_order : int | None = None
                   ) -> list:
    ops = []
    data = {
        'type': 'section_add',
        'uuid': str(uuid.uuid4()),
        'temp_id': temp_id,
        'args': {
            'name': name,
            'project_id': project_id
        }
    }
    if section_order:
        data['args']['section_order'] = section_order
    ops.append(data)
    return ops

def date_from_taskwarrior(date : TasksyncDatetime, timezone : str) -> TodoistSyncDue:
    out = TodoistSyncDue({
        'timezone': timezone,
        'is_recurring': False,
    })
    due_datetime = date.astimezone(ZoneInfo(timezone))
    if due_datetime.hour == 0 and due_datetime.minute == 0:
        out['date'] = date.strftime('%Y-%m-%d')
    else:
        out['date'] = date.strftime(TODOIST_DATETIME_FORMAT)
    return out

def update_taskwarrior(sync_res, taskwarrior_uuids):
    '''
    Update Taskwarrior with Todoist IDs returned by the Sync API

    Note: this only works if you use the taskwarrior UUID as the temp_id in your
    API calls!
    '''
    for taskwarrior_uuid in taskwarrior_uuids:
        if todoist_id := sync_res.get('temp_id_mapping', {}).get(taskwarrior_uuid):
            command = [
                'task',
                'rc.hooks=off', # bypass hooks
                taskwarrior_uuid,
                'modify',
                'todoist={}'.format(str(todoist_id))
            ]
            res = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return


def _check_update(task_old: TaskwarriorTask, task_new: TaskwarriorTask, attr : str) -> bool:
    oldval = getattr(task_old, attr)
    newval = getattr(task_new, attr)
    return newval is not None and (oldval is None or (oldval != newval))

def _check_remove(task_old: TaskwarriorTask, task_new: TaskwarriorTask, attr: str) -> bool:
    oldval = getattr(task_old, attr)
    newval = getattr(task_new, attr)
    return oldval is not None and newval is None
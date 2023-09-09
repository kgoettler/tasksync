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
from tasksync.todoist.api import TodoistSyncDataStore, TodoistSyncAPI
from tasksync.todoist.models import TodoistSyncDue

TODOIST_DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'

def add_item(task: TaskwarriorTask, store: TodoistSyncDataStore) -> list:
    ops = []
    kwargs = {}
    if task.project:
        if project := store.find('projects', name=task.project):
            kwargs['project_id'] = project['id']
        else:
            temp_id = str(uuid.uuid4())
            ops.append(TodoistSyncAPI.create_project(name=task.project, temp_id=temp_id))
            kwargs['project_id'] = temp_id
    if task.due:
        kwargs['due'] = date_from_taskwarrior(task.due, task.timezone) # type: ignore
    if task.priority:
        kwargs['priority'] = task.priority.value + 1 # type: ignore
    if len(task.tags) > 0:
        kwargs['labels'] = task.tags # type: ignore
    ops.append(TodoistSyncAPI.add_item(
        task.description,
        str(task.uuid),
        **kwargs,
    ))
    return ops

def update_item(task_old: TaskwarriorTask, task_new: TaskwarriorTask, store: TodoistSyncDataStore) -> list:
    ops = []
    kwargs = {}

    # Description
    if task_old.description != task_new.description:
        kwargs['content'] = task_new.description

    # Due date
    if _check_update(task_old, task_new, 'due'):
        kwargs['due'] = date_from_taskwarrior(task_new.due, task_new.timezone)  # type: ignore
    elif _check_remove(task_old, task_new, 'due'):
        kwargs['due'] = None

    # Priority
    if _check_update(task_old, task_new, 'priority'):
        kwargs['priority'] = task_new.priority.value + 1 # type: ignore
    elif _check_remove(task_old, task_new, 'priority'):
        kwargs['priority'] = 1

    # Labels
    if _check_update(task_old, task_new, 'tags'):
        kwargs['labels'] = task_new.tags

    # Build payload
    if len(kwargs) > 0:
        ops.append(TodoistSyncAPI.modify_item(
            task_new.todoist,
            **kwargs,
        ))
    return ops

def move_item(task_old: TaskwarriorTask, task_new: TaskwarriorTask, store: TodoistSyncDataStore) -> list:
    ops = []
    kwargs = {}

    # Project
    project_id = None
    # (0, 1) or (1, 1)
    if task_new.project is not None:
        if project := store.find('projects', name=task_new.project):
            project_id = project['id']
            if task_old.project != task_new.project:
                kwargs['project_id'] = project_id
        else:
            # Project does not exist -- we need to create it
            # Use temporary uuid so we can identify it in successive calls, if needed
            project_id = str(uuid.uuid4())
            ops.append(TodoistSyncAPI.create_project(name=task_new.project, temp_id=project_id)) # type: ignore
            kwargs['project_id'] = project_id
    else:
        if project := store.find('projects', name='Inbox'):
            project_id = project['id']
            kwargs['project_id'] = project_id
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
            kwargs['section_id'] = section['id']
            if 'project_id' in kwargs:
                del kwargs['project_id']
        else:
            # Section does not exist -- we need to create it
            section_id = str(uuid.uuid4())
            ops.append(TodoistSyncAPI.create_section(name=task_new.section, temp_id=section_id, project_id=project_id)) # type: ignore
            kwargs['section_id'] = section_id
    elif task_old.section is not None:
        # From API docs:
        # > to move an item from a section to no section, just use the
        # > project_id parameter, with the project it currently belongs to as a
        # > value.
        kwargs['project_id'] = project_id
    
    if len(kwargs) > 0:
        ops.append(TodoistSyncAPI.move_item(
            task_new.todoist,
            **kwargs
        ))
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
        ops.append(TodoistSyncAPI.complete_item(
            task_new.todoist,
            date_completed=None if task_new.end is None else task_new.end.strftime(TODOIST_DATETIME_FORMAT),
        ))
    return ops

def uncomplete_item(task_old: TaskwarriorTask, task_new: TaskwarriorTask, store: TodoistSyncDataStore) -> list:
    ops = []
    if task_old.status == TaskwarriorStatus.COMPLETED and task_new.status != TaskwarriorStatus.COMPLETED:
        ops.append(TodoistSyncAPI.uncomplete_item(
            task_new.todoist, # type: ignore
        ))
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
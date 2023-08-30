#!/usr/bin/env python3

from os.path import basename, dirname, exists, join
import json
import os
import uuid
from datetime import datetime

from todoist import TodoistSync
from tasksync.sync.util import *
from taskw import TaskWarrior

WORK_PROJECT_ID = '2299975668'

# Setup
tw = TaskWarrior()
sync = TodoistSync()
## Get data from taskwarrior and todoist
sync.sync(sync_token='*')

# Load Todoist data
todo_data = sync.load_data()
todo_sections_by_name = todoist_get_section_map(todo_data, by='name')
todo_sections_by_id = todoist_get_section_map(todo_data, by='id')
todo_tasks = todoist_get_task_map(todo_data)

# Get tasks from both systems
tw_tasks = tw.load_tasks()

# 1. Check completed tasks in TW and ensure they are completed in Todoist
for task in tw_tasks['completed']:
    if 'todoist' in task and task['todoist'] in todo_tasks:
        sync.complete_item(
            id=task['todoist'],
            temp_id=str(uuid.uuid4()),
            date_completed=datetime.strptime('%Y%m%dT%H%M%SZ').strftime('%Y-%m-%dT%H:%M:%SZ')
        )

# 2. Check pending tasks in TW and ensure they exist in Todoist
# -if they don't, create them
# -if they do, ensure their descriptions are up to date
temp_id_mapping = {}
for task in tw_tasks['pending']:
    if 'todoist' not in task or task['todoist'] not in todo_tasks:
        args = {}
        if 'project' in task:
            if task['project'] not in todo_sections_by_name:
                args['name'] = task['project']
                args['temp_id'] = str(uuid.uuid4())
                args['project_id'] = WORK_PROJECT_ID
                sync.add_section(**args)
            else:
                args['temp_id'] = todo_sections_by_name[task['project']]['id']
        newargs = {
            **convert_taskwarrior_task(task),
            'temp_id': str(uuid.uuid4()),
            'project_id': WORK_PROJECT_ID,
        }
        if 'temp_id' in args:
            newargs['section_id'] = args['temp_id']
        if 'id' in newargs:
            del newargs['id']
        temp_id_mapping[newargs['temp_id']] = task
        sync.add_item(**newargs)
    else:
        # Check if task needs to be updated in Todoist; if so, post the update
        task_todo = todo_tasks[task['todoist']]
        # NOTE: Implicit here is that if there is a discrepancy, we give
        # priority to information in TaskWarrior Unfortunately without a 'last
        # modified' timestamp in Todoist we have to pick one
        args = {
            **convert_taskwarrior_task(task),
            'temp_id': str(uuid.uuid4()),
        }
        # Only sync the update if the description or due date has changed
        if ((task['description'] != task_todo['content']) or
                (task_todo['due'] is not None and 'due' in task and (parse_todoist_date_string(args['due']['date']) != parse_todoist_date_string(task_todo['due']['date'])))
                ):
            sync.update_item(**args)

        # Determine if the task needs to be moved to another section
        if 'project' in task:
            # If taskwarrior project does not exist as a section, make it
            if task['project'] not in todo_sections_by_name:
                args = {
                    'name': task['project'],
                    'temp_id': str(uuid.uuid4()),
                    'project_id': WORK_PROJECT_ID,
                }
                sync.add_section(**args)
                newargs = {
                    'id': task['todoist'],
                    'temp_id': str(uuid.uuid4()),
                    'section_id': args['temp_id']
                }
                sync.move_item(**newargs)
            # else, taskwarrior project does exist so:
            # if todoist task is not in a section or is in the wrong one, move it
            elif task_todo['section_id'] is None or task['project'] != todo_sections_by_id[task_todo['section_id']]['name']:
                sync.move_item(
                    id=task['todoist'],
                    temp_id=str(uuid.uuid4()),
                    section_id=todo_sections_by_name[task['project']]['id']
                )

# 3. Sync to Todoist
# - Add ids of all newly created Todoist tasks to associated TW tasks
res = sync.run()
for key, task in temp_id_mapping.items():
    task['todoist'] = res['temp_id_mapping'][key]
    tw.task_update(task)

# 4. Check all items in Todoist, add missing ones to TaskWarrior
existing_ids = set([x['todoist'] for x in tw_tasks['pending'] if 'todoist' in x])
new_tasks = []
for todoist_id, item in todo_tasks.items():
    if todoist_id not in existing_ids and not item['is_deleted']:
        task = tw.task_add(
            **convert_todoist_task(item)
        )
        new_tasks.append(task)

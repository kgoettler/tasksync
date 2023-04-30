#!/usr/bin/env python3

from os.path import basename, dirname, exists, join
import json
import os
import uuid
from datetime import datetime
from enum import Enum

from todoist import TodoistSync
from util import *
from taskw import TaskWarrior

WORK_PROJECT_ID = '2299975668'

class TaskType(Enum):
    TODOIST = 0
    TASKWARRIOR = 1

class Translator:

    def __init__(self, task_tw, task_todo):
        self.task_tw = task_tw
        self.task_todo = task_todo
        return
    
    def convert_todoist_to_taskwarrior(self, priority=TaskType.TODOIST):
        return

    def convert_taskwarrior_to_todoist(self, priority=TaskType.TASKWARRIOR):
        return

# Setup
tw = TaskWarrior()
sync = TodoistSync()

# Load Todoist data
sync.sync(sync_token='*')
todo_data = sync.load_data()
todo_sections_by_name = todoist_get_section_map(todo_data, by='name')
todo_sections_by_id = todoist_get_section_map(todo_data, by='id')
todo_tasks = todoist_get_task_map(todo_data)

# Load TaskWarrior data
tw_tasks = tw.load_tasks()

to_create, to_update = [], []
for todoist_id, task in todo_tasks.items():
    # Find associated task in TaskWarrior
    task_match = None
    for task_tw in tw_tasks['pending']:
        if task_tw.get('todoist', None) == todoist_id:
            task_match = task_tw
            break
        elif task_tw['description'] == task['content']:
            task_match = task_tw
    # If no matching task is found, create the task
    if task_match is None:
        to_create.append(convert_todoist_task(task, sections=todo_data['sections']))
        continue
    # Otherwise ensure the task is up-to-date
    update = False
    updated_task = {**task_match}
    for key, value in convert_todoist_task(task, sections=todo_data['sections']).items():
        if updated_task.get(key) != value:
            print(key, updated_task.get(key), value)
            updated_task[key] = value
            update = True
    if update:
        to_update.append(updated_task)
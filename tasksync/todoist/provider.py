from __future__ import annotations

from tasklib import Task, TaskWarrior

from tasksync.models import TasksyncDatetime
from tasksync.taskwarrior.models import TaskwarriorTask, TaskwarriorPriority
from tasksync.todoist.adapter import (
    add_item,
    update_item,
    move_item,
    delete_item,
    complete_item,
    uncomplete_item,
    update_taskwarrior
)
from tasksync.todoist.api import TodoistSync, TodoistSyncDataStore
from tasksync.todoist.models import TodoistSyncTaskDict

class TodoistProvider:

    def __init__(self, store=None, api=None):
        self.commands = []
        self.store = TodoistSyncDataStore() if store is None else store
        self.api = TodoistSync(store=self.store) if api is None else api

    def on_add(self, task : TaskwarriorTask) -> tuple[str,str]:
        self.commands += add_item(task, self.store)
        feedback = 'Todoist: item created'
        return task.to_taskwarrior(), feedback
    
    def on_modify(self, task_old : TaskwarriorTask, task_new : TaskwarriorTask) -> tuple[str,str]:
        # If task doesn't have a todoist id just create it and move on
        if task_new.todoist is None:
            return self.on_add(task_new)[0], 'Todoist: item created (did not exist)'
        
        # Record any supported updates
        actions = []
        commands = []
        if ops := update_item(task_old, task_new, self.store):
            commands += ops
            actions.append('updated')
        if ops := move_item(task_old, task_new, self.store):
            commands += ops
            actions.append('moved')
        if ops := delete_item(task_old, task_new, self.store):
            commands += ops
            actions.append('deleted')
        elif ops := complete_item(task_old, task_new, self.store):
            commands += ops
            actions.append('completed')
        elif ops := uncomplete_item(task_old, task_new, self.store):
            commands += ops
            actions.append('uncompleted')
        if len(commands) == 0:
            feedback = 'Todoist: update not required'
        else:
            if len(actions) == 1:
                feedback = 'Todoist: item {}'.format(actions[0])
            elif len(actions) == 2:
                feedback = 'Todoist: item {} and {}'.format(*actions)
            else:
                feedback = 'Todoist: item {}, and {}'.format(
                    ', '.join(actions[0:-1]),
                    actions[-1],
                )
        self.commands += commands
        return task_new.to_taskwarrior(exclude_id=True), feedback

    def pull(self) -> None:
        _ = self.api.pull(resource_types=['items'])
        tw = TaskWarrior()
        tw.overrides.update({'hooks': 'off'})

        # Get only those taskwarrior tasks with Todoist IDs
        known_ids = set((task['todoist'] for task in tw.tasks))
        if None in known_ids:
            known_ids.remove(None)
        for todoist_task in self.store.find_all('items'):
            if todoist_task['id'] in known_ids:
                # Update from todoist
                task = update_from_todoist(
                    tw,
                    todoist_task,
                    self.store
                )
                if task:
                    task.save()
            # Else if task does not exist, but is not deleted or completed
            elif not todoist_task['is_deleted'] and todoist_task['completed_at'] is None:
                task = create_from_todoist(
                    tw,
                    todoist_task,
                    self.store,
                )
                task.save()

        return
    
    def push(self) -> None:
        res = self.api.push(commands=self.commands)
        
        # Check to see if any item_add commands were included
        # (in this case we need to update Taskwarrior)
        new_uuids = [x.get('temp_id') for x in self.commands if x['type'] == 'item_add']
        if len(new_uuids) > 0:
            update_taskwarrior(res, new_uuids)

        # Clear out commands
        self.commands.clear()
        return

    @property 
    def updated(self):
        return len(self.commands) > 0

def create_from_todoist(tw : TaskWarrior, todoist_task : TodoistSyncTaskDict, store : TodoistSyncDataStore) -> Task:
    out : Task = Task(
        tw,
        description=todoist_task['content'],
    )
    # Project ID
    if todoist_task['project_id'] is not None:
        if todoist_project := store.find('projects', id=todoist_task['project_id']):
            out['project'] = todoist_project['name']

    # Priority 
    if todoist_task['priority'] is not None:
        out['priority'] = convert_priority(todoist_task['priority'])

    # Labels 
    if len(todoist_task['labels']) > 0:
        out['tags'] = set(todoist_task['labels'])

    # Due date
    if todoist_task['due'] is not None:
        if due := TasksyncDatetime.from_todoist(todoist_task['due']):
            out['due'] = out.deserialize_due(due.to_taskwarrior())

    # Section
    if section_id := todoist_task['section_id']:
        if todoist_section := store.find('sections', id=section_id):
            out['section'] = todoist_section['name']
    
    out['todoist'] = todoist_task['id']

    return out
        

def update_from_todoist(tw : TaskWarrior, todoist_task : TodoistSyncTaskDict, store : TodoistSyncDataStore) -> Task | None:

    task = tw.tasks.get(todoist=todoist_task['id'])

    # Ignore deleted tasks
    if task.deleted and todoist_task['is_deleted']:
        return
    
    # Update status
    # - Close completed tasks
    if not task.completed and todoist_task['completed_at'] is not None:
        task.done()
        #task._data['end'] = TasksyncDatetime.from_todoist(todoist_task['completed_at']).to_taskwarrior()
    
    # Update description
    if task['description'] != todoist_task['content']:
        task['description'] = todoist_task['content']
    
    # Update project
    if project := store.find('projects', id=todoist_task['project_id']):
        if task['project'] != project['name']:
            task['project'] = project['name']
    
    # Update priority
    tw_priority = 0 if task['priority'] is None else TaskwarriorPriority[task['priority']].value
    if (tw_priority + 1) != todoist_task['priority']:
        task['priority'] = convert_priority(todoist_task['priority'])

    # Update tags
    if task['tags'] != set(todoist_task['labels']):
        task['tags'] = set(todoist_task['labels'])

    # Update due
    tw_due = None if task['due'] is None else task.serialize_due(task['due'])
    todoist_due = todoist_task['due']
    if todoist_due is not None:
        todoist_due = TasksyncDatetime.from_todoist(todoist_due).to_taskwarrior()
    if tw_due != todoist_due:
        task['due'] = None if todoist_due is None else task.deserialize_due(todoist_due)

    # Update section

    # Update todoist uda
    task['todoist'] = todoist_task['id']
    return task


def convert_labels(labels: list[str]) -> set:
    return set(labels)

def convert_priority(priority : int):
    priorities = [None, 'L', 'M', 'H']
    return priorities[priority-1]


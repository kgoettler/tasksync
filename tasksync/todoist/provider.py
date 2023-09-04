from __future__ import annotations

from tasklib import Task

from tasksync.taskwarrior.models import TaskwarriorTask
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

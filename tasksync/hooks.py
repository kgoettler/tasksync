import json

from taskwarrior.models import TaskwarriorTask
from adapters.todoist import (
    add_item,
    update_item,
    move_item,
    delete_item,
    complete_item,
    uncomplete_item,
)

def on_add(task_json_input, sync, client) -> tuple[str, str]:
    '''
    on-add hook for Taskwarrior

    Parameters
    ----------
    task_json_input : str
        Input str emitted by Taskwarrior on task add
    api : TodoistAPI
        api object

    Returns
    -------
    task_json_final : str
        Updated input str with newly added fields
    feedback : str
        Feedback str, printed by Taskwarrior after hook is completed
    '''
    # Preallocate output
    feedback = ''

    # Read input
    task = TaskwarriorTask.from_taskwarrior(json.loads(task_json_input))

    # Create task in Todoist
    commands = add_item(task, sync.store)
    client.connect()
    client.send(commands)
    client.close()

    # Copy resulting id back
    feedback = 'Todoist: item created'
    return (task.to_taskwarrior(), feedback)


def on_modify(task_json_input, task_json_output, sync, client) -> tuple[str, str]:
    '''
    on-modify hook for Taskwarrior to sync local changes to Todoist

    Parameters
    ----------
    task_json_input : str
        Original JSON str of task emitted by Taskwarrior
    task_json_output : str
        Modified JSON str of task emitted by Taskwarrior
    api : TodoistAPI
        api object

    Returns
    -------
    task_json_final : str
        Updated JSON str with newly updated fields
    feedback : str
        Feedback str, printed by Taskwarrior after hook is completed
    '''
    # Preallocate output
    feedback = ''

    # Read inputs
    task_old = TaskwarriorTask.from_taskwarrior(json.loads(task_json_input))
    task_new = TaskwarriorTask.from_taskwarrior(json.loads(task_json_output))

    # If task doesn't have a todoist id just create it and move on
    if task_new.todoist is None:
        return on_add(task_json_output, sync, client)[0], 'Todoist: item added (did not exist)'

    actions = []
    commands = []
    if ops := update_item(task_old, task_new, sync.store):
        commands += ops
        actions.append('updated')
    if ops := move_item(task_old, task_new, sync.store):
        commands += ops
        actions.append('moved')
    if ops := delete_item(task_old, task_new, sync.store):
        commands += ops
        actions.append('deleted')
    elif ops := complete_item(task_old, task_new, sync.store):
        commands += ops
        actions.append('completed')
    elif ops := uncomplete_item(task_old, task_new, sync.store):
        commands += ops
        actions.append('uncompleted')
    if len(commands) == 0:
        feedback = 'Todoist: update not required'
    else:
        client.connect()
        if len(actions) == 1:
            feedback = 'Todoist: item {}'.format(actions[0])
        elif len(actions) == 2:
            feedback = 'Todoist: item {} and {}'.format(*actions)
        elif len(actions) >= 3:
            feedback = 'Todoist: item {}, and {}'.format(
                ', '.join(actions[0:-1]),
                actions[-1],
            )
        client.send(commands)
        client.close()

    return (task_new.to_taskwarrior(exclude_id=True), feedback)
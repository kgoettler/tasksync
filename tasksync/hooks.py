import json

from tasksync.taskwarrior.models import TaskwarriorTask

def on_add(task_json_input, provider) -> tuple[str, str]:
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
    # Read input
    task = TaskwarriorTask.from_taskwarrior(json.loads(task_json_input))

    return provider.on_add(task)


def on_modify(task_json_input, task_json_output, provider) -> tuple[str, str]:
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
    # Read inputs
    task_old = TaskwarriorTask.from_taskwarrior(json.loads(task_json_input))
    task_new = TaskwarriorTask.from_taskwarrior(json.loads(task_json_output))

    return provider.on_modify(task_old, task_new)
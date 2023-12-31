from __future__ import annotations

import json

from tasksync.models import TasksyncDatetime
from todoist_api_python.models import Task as TodoistTask, Due as TodoistDueDate
from tasksync.taskwarrior.models import TaskwarriorDict, TaskwarriorTask

def get_taskwarrior_input(return_type='dict') -> TaskwarriorDict | str:
    data = TaskwarriorDict(**{
        "id": 2,
        "description": "Test case w/ due_date",
        "due": "20230828T040000Z",
        "entry": "20230827T212930Z",
        "modified": "20230827T212931Z",
        "project": "Inbox",
        "priority": "M",
        "status": "pending",
        "timezone": "America/New_York",
        "todoist": '7173209653',
        "uuid": "2d0fc886-3a8e-478c-a323-5d13de45e254",
        "tags": [
            "test2"
        ],
        "urgency": 13.2049
    })
    if return_type == 'dict':
        return data
    else:
        return json.dumps(data)

def get_task(due_datetime=False):
    task = TaskwarriorTask.from_taskwarrior(json_data=get_taskwarrior_input())
    if due_datetime:
        task.due = TasksyncDatetime.from_taskwarrior("20230828T130000Z")
    return task
                
def get_todoist(due_datetime=False):
    todoist = TodoistTask(**
        {
            'assignee_id': None,
            'assigner_id': None,
            'comment_count': 0,
            'is_completed': False,
            'content': 'Test case w/ due_date',
            'created_at': '2023-08-27T21:29:31.440088Z',
            'creator_id': '41348840',
            'description': '',
            'due': TodoistDueDate(**{
                'date': '2023-08-28',
                'is_recurring': False,
                'string': '2023-08-28',
                'datetime': None,
                'timezone': None
            }),
            'id': '7173209653',
            'labels': ['test2'],
            'order': 13,
            'parent_id': None,
            'priority': 3,
            'project_id': '2299975638',
            'section_id': None,
            'sync_id': None,
            'url': 'https://todoist.com/showTask?id=7173209653',
        }
    )
    if due_datetime:
        todoist.due = TodoistDueDate(**{
            'date': '2023-08-28',
            'is_recurring': False,
            'string': '2023-08-28 09:00',
            'datetime': '2023-08-28T13:00:00Z',
            'timezone': 'America/New_York'
        })
    return todoist
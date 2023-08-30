#!/usr/bin/env python3

import pytest

#from todoist_api_python.models import Task as TodoistTask, Due as TodoistDue
from tasksync.models import (
    TaskwarriorTask,
    TaskwarriorDatetime,
    TaskwarriorPriority,
    TaskwarriorStatus,
)

from test_data import get_task, get_todoist, get_taskwarrior_input

class TestTaskwarrior:

    def test_from_taskwarrior_str(self):
        json_data = get_taskwarrior_input(return_type='str')
        _ = TaskwarriorTask.from_taskwarrior(json_data=json_data)
        assert True

    @pytest.mark.parametrize('due_datetime', [True, False])
    def test_from_taskwarrior(self, due_datetime):
        task = get_task(due_datetime=due_datetime)
        assert task.id == 2
        assert isinstance(task.due, TaskwarriorDatetime)
        if not due_datetime:
            assert task.due.strftime('%H%M%S') == '040000'
        else:
            assert task.due.strftime('%H%M%S') == '130000' 
        assert task.due.tzinfo.key == 'UTC' # type: ignore
        assert isinstance(task.priority, TaskwarriorPriority)
        assert task.priority == TaskwarriorPriority.M
        assert task.priority.value == 2
        assert task.priority.to_todoist() == 3
        assert isinstance(task.status, TaskwarriorStatus)
        assert task.status == TaskwarriorStatus.PENDING
        assert isinstance(task.tags, list)
        assert len(task.tags) == 1
        assert task.tags[0] == 'test2'
        assert task.timezone == 'America/New_York'
        assert isinstance(task.todoist, int)
        assert task.todoist == 7173209653

    @pytest.mark.parametrize('due_datetime', [True, False])
    def test_to_todoist_api_kwargs(self, due_datetime):
        task = get_task(due_datetime=due_datetime)
        kwargs = task.to_todoist_api_kwargs()
        assert kwargs['task_id'] == str(task.todoist)
        assert kwargs['content'] == task.description
        assert not kwargs['is_completed']
        assert kwargs['labels'] == task.tags
        assert kwargs['priority'] == 3
        if not due_datetime:
            assert kwargs['due_date'] == '2023-08-28'
        else:
            assert kwargs['due_datetime'] == "2023-08-28T13:00:00.000000Z"

    @pytest.mark.parametrize('due_datetime', [True, False])
    def test_from_todoist(self, due_datetime):
        task = get_task(due_datetime=due_datetime)
        todoist = get_todoist(due_datetime=due_datetime)
        task_from_todoist = TaskwarriorTask.from_todoist(todoist)
        assert isinstance(task_from_todoist.due, TaskwarriorDatetime)
        assert task_from_todoist.due.strftime('%Y%m%dT%H%M%SZ') == task.due.strftime('%Y%m%dT%H%M%SZ') # type: ignore
        assert task_from_todoist.due.tzinfo.key == 'UTC' # type: ignore
        assert isinstance(task_from_todoist.priority, TaskwarriorPriority)
        assert task_from_todoist.priority == TaskwarriorPriority.M
        assert task_from_todoist.priority.value == 2
        assert task_from_todoist.priority.to_todoist() == 3
        assert isinstance(task_from_todoist.status, TaskwarriorStatus)
        assert task_from_todoist.status == TaskwarriorStatus.PENDING
        assert isinstance(task_from_todoist.tags, list)
        assert len(task_from_todoist.tags) == 1
        assert task_from_todoist.tags[0] == 'test2'
        assert task_from_todoist.todoist == 7173209653
    
    def test_update(self):
        task = get_task()
        desc = 'New description'
        task.update(description=desc)
        assert task.description == desc

    def test_to_json(self):
        json_data = '{"description":"Test 1","entry":"20230827T232837Z","id":3,"modified":"20230827T232837Z","status":"pending","todoist":123,"urgency":0,"uuid":"5da82ec9-e85b-47ac-b0c6-9e3486f9fb74"}'
        task = TaskwarriorTask.from_taskwarrior(json_data)
        assert json_data == task.to_json(exclude_id=False, sort_keys=True).replace(', ', ',').replace(': ', ':')
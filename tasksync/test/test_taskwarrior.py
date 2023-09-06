#!/usr/bin/env python3

import pytest

from tasksync.models import TasksyncDatetime
from tasksync.taskwarrior.models import (
    TaskwarriorPriority,
    TaskwarriorStatus,
    TaskwarriorTask
)

from test_data import get_task, get_taskwarrior_input

class TestTaskwarrior:

    def test_from_taskwarrior_str(self):
        json_data = get_taskwarrior_input(return_type='str')
        _ = TaskwarriorTask.from_taskwarrior(json_data=json_data)
        assert True

    @pytest.mark.parametrize('due_datetime', [True, False])
    def test_from_taskwarrior(self, due_datetime):
        task = get_task(due_datetime=due_datetime)
        assert task.id == 2
        assert isinstance(task.due, TasksyncDatetime)
        if not due_datetime:
            assert task.due.strftime('%H%M%S') == '040000'
        else:
            assert task.due.strftime('%H%M%S') == '130000' 
        assert task.due.tzinfo.key == 'UTC' # type: ignore
        assert isinstance(task.priority, TaskwarriorPriority)
        assert task.priority == TaskwarriorPriority.M
        assert task.priority.value == 2
        assert isinstance(task.status, TaskwarriorStatus)
        assert task.status == TaskwarriorStatus.PENDING
        assert isinstance(task.tags, list)
        assert len(task.tags) == 1
        assert task.tags[0] == 'test2'
        assert task.timezone == 'America/New_York'
        assert isinstance(task.todoist, str)
        assert task.todoist == '7173209653'

    def test_update(self):
        task = get_task()
        desc = 'New description'
        task.update(description=desc)
        assert task.description == desc

    def test_to_json(self):
        json_data = '{"description":"Test 1","entry":"20230827T232837Z","id":3,"modified":"20230827T232837Z","status":"pending","todoist":123,"urgency":0,"uuid":"5da82ec9-e85b-47ac-b0c6-9e3486f9fb74"}'
        task = TaskwarriorTask.from_taskwarrior(json_data)
        assert json_data == task.to_taskwarrior(exclude_id=False, sort_keys=True).replace(', ', ',').replace(': ', ':')
import pytest
from types import SimpleNamespace
import json

from tasksync.hooks import on_add, on_modify

class DummyAPI:
    def __init__(self):
        return
    
    def add_task(self, **kwargs):
        return SimpleNamespace(
            id=123,
        )
    
    def delete_task(self, **kwargs):
        return SimpleNamespace()
    
    def update_task(self, **kwargs):
        return SimpleNamespace(
            id=123,
        )

def test_on_add():
    task_json, feedback = on_add(
        '{"id":3,"description":"Test 1","entry":"20230827T232837Z","modified":"20230827T232837Z","status":"pending","uuid":"5da82ec9-e85b-47ac-b0c6-9e3486f9fb74","urgency":0}',
        DummyAPI(),
    )
    task_json = json.loads(task_json)
    assert task_json['todoist'] == 123
    assert task_json['timezone'] == 'America/New_York'
    assert feedback == 'Todoist: task created'


def test_on_modify_update():
    task_json, feedback = on_modify(
        '{"id":3,"description":"Test 1","entry":"20230827T232837Z","modified":"20230827T232837Z","status":"pending","uuid":"5da82ec9-e85b-47ac-b0c6-9e3486f9fb74","urgency":0,"todoist":123}',
        '{"id":3,"description":"Test Update","entry":"20230827T232837Z","modified":"20230827T233228Z","status":"pending","uuid":"5da82ec9-e85b-47ac-b0c6-9e3486f9fb74","urgency":0,"todoist":123}',
        DummyAPI(),
    )
    task_json = json.loads(task_json)
    assert task_json['todoist'] == 123
    assert task_json['timezone'] == 'America/New_York'
    assert task_json['description'] == 'Test Update'
    assert feedback == 'Todoist: task updated'

def test_on_modify_delete():
    task_json, feedback = on_modify(
        '{"id":3,"description":"Test 1","entry":"20230827T232837Z","modified":"20230827T232837Z","status":"pending","uuid":"5da82ec9-e85b-47ac-b0c6-9e3486f9fb74","urgency":0,"todoist":123}',
        '{"id":3,"description":"Test 1","entry":"20230827T232837Z","modified":"20230827T233228Z","status":"deleted","uuid":"5da82ec9-e85b-47ac-b0c6-9e3486f9fb74","urgency":0,"todoist":123}',
        DummyAPI(),
    )
    task_json = json.loads(task_json)
    assert feedback == 'Todoist: task deleted'

def test_on_modify_missing():
    task_json, feedback = on_modify(
        '{"id":3,"description":"Test 1","entry":"20230827T232837Z","modified":"20230827T232837Z","status":"pending","uuid":"5da82ec9-e85b-47ac-b0c6-9e3486f9fb74","urgency":0}',
        '{"id":3,"description":"Test Update","entry":"20230827T232837Z","modified":"20230827T233228Z","status":"pending","uuid":"5da82ec9-e85b-47ac-b0c6-9e3486f9fb74","urgency":0}',
        DummyAPI(),
    )
    task_json = json.loads(task_json)
    assert task_json['description'] == 'Test Update'
    assert task_json['todoist'] == 123
    assert task_json['timezone'] == 'America/New_York'
    assert feedback == 'Todoist: task created (did not exist)' 

def test_on_modify_noop():
    task_json, feedback = on_modify(
        '{"id":3,"description":"Test 1","entry":"20230827T232837Z","modified":"20230827T232837Z","status":"pending","uuid":"5da82ec9-e85b-47ac-b0c6-9e3486f9fb74","urgency":0,"todoist":123}',
        '{"id":3,"description":"Test 1","entry":"20230827T232837Z","modified":"20230828T232837Z","status":"pending","uuid":"5da82ec9-e85b-47ac-b0c6-9e3486f9fb74","urgency":0,"todoist":123}',
        DummyAPI(),
    )
    task_json = json.loads(task_json)
    assert feedback == 'Todoist: update not required'
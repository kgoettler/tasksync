import pytest

from os.path import dirname, join
import json

from hooks import on_add, on_modify
from todoist.provider import TodoistProvider
from todoist.api import TodoistSyncDataStore

from test_data import get_task

class DummySyncAPI:
    def __init__(self):
        self.commands = []
        return
    
    def add_project(self, name, temp_id, **kwargs):
        return
    
    def push(self):
        temp_ids = [x['temp_id'] for x in self.commands if 'temp_id' in x]
        return  {
            'temp_id_mapping': {temp_id: 123 for temp_id in temp_ids} 
        }
    
    def pull(self, resource_types=None):
        return
    

@pytest.fixture
def provider():
    provider = TodoistProvider(
        store=TodoistSyncDataStore(basedir=join(dirname(__file__), 'data')),
        api=DummySyncAPI(),
    )
    return provider

@pytest.fixture
def task():
    return get_task()

@pytest.fixture
def old_task():
    return get_task()

@pytest.fixture
def new_task():
    return get_task()


class TestHooks:

    def test_on_add(self, provider):
        task_json, feedback = on_add(
            '{"id":3,"description":"Test 1","entry":"20230827T232837Z","modified":"20230827T232837Z","project":"Inbox","status":"pending","uuid":"5da82ec9-e85b-47ac-b0c6-9e3486f9fb74","urgency":0}',
            provider,
        )
        task_json = json.loads(task_json)
        #assert task_json['todoist'] == 123
        #assert task_json['timezone'] == 'America/New_York'
        assert feedback == 'Todoist: item created'

    def test_on_add_new_project(self, provider):
        task_json, feedback = on_add(
            '{"id":3,"description":"Test 1","entry":"20230827T232837Z","modified":"20230827T232837Z","project":"Work","status":"pending","uuid":"5da82ec9-e85b-47ac-b0c6-9e3486f9fb74","urgency":0}',
            provider,
        )
        task_json = json.loads(task_json)
        #assert task_json['todoist'] == 123
        #assert task_json['timezone'] == 'America/New_York'
        assert task_json['project'] == 'Work'
        assert feedback == 'Todoist: item created'

    def test_on_modify_update(self, provider):
        task_json, feedback = on_modify(
            '{"id":3,"description":"Test 1","entry":"20230827T232837Z","modified":"20230827T232837Z","status":"pending","uuid":"5da82ec9-e85b-47ac-b0c6-9e3486f9fb74","urgency":0,"todoist":123}',
            '{"id":3,"description":"Test Update","entry":"20230827T232837Z","modified":"20230827T233228Z","status":"pending","uuid":"5da82ec9-e85b-47ac-b0c6-9e3486f9fb74","urgency":0,"todoist":123}',
            provider,
        )
        task_json = json.loads(task_json)
        assert task_json['todoist'] == 123
        assert task_json['description'] == 'Test Update'
        assert feedback == 'Todoist: item updated'

    def test_on_modify_delete(self, provider):
        task_json, feedback = on_modify(
            '{"id":3,"description":"Test 1","entry":"20230827T232837Z","modified":"20230827T232837Z","status":"pending","uuid":"5da82ec9-e85b-47ac-b0c6-9e3486f9fb74","urgency":0,"todoist":123}',
            '{"id":3,"description":"Test 1","entry":"20230827T232837Z","modified":"20230827T233228Z","status":"deleted","uuid":"5da82ec9-e85b-47ac-b0c6-9e3486f9fb74","urgency":0,"todoist":123}',
            provider,
        )
        task_json = json.loads(task_json)
        assert feedback == 'Todoist: item deleted'

    def test_on_modify_missing(self, provider):
        task_json, feedback = on_modify(
            '{"id":3,"description":"Test 1","entry":"20230827T232837Z","modified":"20230827T232837Z","status":"pending","uuid":"5da82ec9-e85b-47ac-b0c6-9e3486f9fb74","urgency":0}',
            '{"id":3,"description":"Test Update","entry":"20230827T232837Z","modified":"20230827T233228Z","status":"pending","uuid":"5da82ec9-e85b-47ac-b0c6-9e3486f9fb74","urgency":0}',
            provider,
        )
        task_json = json.loads(task_json)
        assert task_json['description'] == 'Test Update'
        #assert task_json['todoist'] == 123
        #assert task_json['timezone'] == 'America/New_York'
        assert feedback == 'Todoist: item created (did not exist)' 

    def test_on_modify_noop(self, provider):
        task_json, feedback = on_modify(
            '{"id":3,"description":"Test 1","entry":"20230827T232837Z","modified":"20230827T232837Z","status":"pending","uuid":"5da82ec9-e85b-47ac-b0c6-9e3486f9fb74","urgency":0,"todoist":123}',
            '{"id":3,"description":"Test 1","entry":"20230827T232837Z","modified":"20230828T232837Z","status":"pending","uuid":"5da82ec9-e85b-47ac-b0c6-9e3486f9fb74","urgency":0,"todoist":123}',
            provider,
        )
        task_json = json.loads(task_json)
        assert feedback == 'Todoist: update not required'


    def test_on_modify_move(self, provider):
        task_json, feedback = on_modify(
            '{"id":3,"description":"Test 1","entry":"20230827T232837Z","modified":"20230827T232837Z","project":"Inbox","status":"pending","uuid":"5da82ec9-e85b-47ac-b0c6-9e3486f9fb74","urgency":0,"todoist":123}',
            '{"id":3,"description":"Test 1","entry":"20230827T232837Z","modified":"20230828T232837Z","project":"Personal","status":"pending","uuid":"5da82ec9-e85b-47ac-b0c6-9e3486f9fb74","urgency":0,"todoist":123}',
            provider,
        )
        task_json = json.loads(task_json)
        assert feedback == 'Todoist: item moved'

    def test_on_modify_complete(self, provider):
        task_json, feedback = on_modify(
            '{"id":3,"description":"Test 1","entry":"20230827T232837Z","modified":"20230827T232837Z","status":"pending","uuid":"5da82ec9-e85b-47ac-b0c6-9e3486f9fb74","urgency":0,"todoist":123}',
            '{"id":3,"description":"Test 1","entry":"20230827T232837Z","modified":"20230828T232837Z","status":"completed","uuid":"5da82ec9-e85b-47ac-b0c6-9e3486f9fb74","urgency":0,"todoist":123}',
            provider,
        )
        task_json = json.loads(task_json)
        assert feedback == 'Todoist: item completed'
    
    def test_on_modify_uncomplete(self, provider):
        task_json, feedback = on_modify(
            '{"id":3,"description":"Test 1","entry":"20230827T232837Z","modified":"20230828T232837Z","status":"completed","uuid":"5da82ec9-e85b-47ac-b0c6-9e3486f9fb74","urgency":0,"todoist":123}',
            '{"id":3,"description":"Test 1","entry":"20230827T232837Z","modified":"20230827T232837Z","status":"pending","uuid":"5da82ec9-e85b-47ac-b0c6-9e3486f9fb74","urgency":0,"todoist":123}',
            provider,
        )
        task_json = json.loads(task_json)
        assert feedback == 'Todoist: item uncompleted'

    def test_on_modify_two_op(self, provider):
        task_json, feedback = on_modify(
            '{"id":3,"description":"Test 1","entry":"20230827T232837Z","modified":"20230827T232837Z","status":"pending","uuid":"5da82ec9-e85b-47ac-b0c6-9e3486f9fb74","urgency":0,"todoist":123}',
            '{"id":3,"description":"Test 2","entry":"20230827T232837Z","modified":"20230827T232837Z","status":"completed","uuid":"5da82ec9-e85b-47ac-b0c6-9e3486f9fb74","urgency":0,"todoist":123}',
            provider,
        )
        task_json = json.loads(task_json)
        assert feedback == 'Todoist: item updated and completed'

    def test_on_modify_three_op(self, provider):
        task_json, feedback = on_modify(
            '{"id":3,"description":"Test 1","entry":"20230827T232837Z","modified":"20230827T232837Z","project":"Inbox","status":"pending","uuid":"5da82ec9-e85b-47ac-b0c6-9e3486f9fb74","urgency":0,"todoist":123}',
            '{"id":3,"description":"Test 2","entry":"20230827T232837Z","modified":"20230827T232837Z","project":"Personal","status":"completed","uuid":"5da82ec9-e85b-47ac-b0c6-9e3486f9fb74","urgency":0,"todoist":123}',
            provider,
        )
        task_json = json.loads(task_json)
        assert feedback == 'Todoist: item updated, moved, and completed'
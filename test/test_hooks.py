import pytest

from os.path import dirname, join
import json

from tasksync.hooks import on_add, on_modify
from tasksync.server import TasksyncClient
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
    
class DummySync:

    def __init__(self):
        self.api = DummySyncAPI()
        self.store = TodoistSyncDataStore(basedir=join(dirname(__file__), 'data'))


@pytest.fixture
def task():
    return get_task()

@pytest.fixture
def old_task():
    return get_task()

@pytest.fixture
def new_task():
    return get_task()

@pytest.fixture
def sync():
    return DummySync()

@pytest.fixture
def client():
    return TasksyncClient()

@pytest.mark.skip(reason="Need to determine how to test sockets")
class TestHooks:

    def test_on_add(self, sync, client):
        task_json, feedback = on_add(
            '{"id":3,"description":"Test 1","entry":"20230827T232837Z","modified":"20230827T232837Z","project":"Inbox","status":"pending","uuid":"5da82ec9-e85b-47ac-b0c6-9e3486f9fb74","urgency":0}',
            sync,
            client,
        )
        task_json = json.loads(task_json)
        #assert task_json['todoist'] == 123
        #assert task_json['timezone'] == 'America/New_York'
        assert feedback == 'Todoist: item created'

    def test_on_add_new_project(self, sync, client):
        task_json, feedback = on_add(
            '{"id":3,"description":"Test 1","entry":"20230827T232837Z","modified":"20230827T232837Z","project":"Work","status":"pending","uuid":"5da82ec9-e85b-47ac-b0c6-9e3486f9fb74","urgency":0}',
            sync,
            client,
        )
        task_json = json.loads(task_json)
        #assert task_json['todoist'] == 123
        #assert task_json['timezone'] == 'America/New_York'
        assert task_json['project'] == 'Work'
        assert feedback == 'Todoist: item created'

    def test_on_modify_update(self, sync, client):
        task_json, feedback = on_modify(
            '{"id":3,"description":"Test 1","entry":"20230827T232837Z","modified":"20230827T232837Z","status":"pending","uuid":"5da82ec9-e85b-47ac-b0c6-9e3486f9fb74","urgency":0,"todoist":123}',
            '{"id":3,"description":"Test Update","entry":"20230827T232837Z","modified":"20230827T233228Z","status":"pending","uuid":"5da82ec9-e85b-47ac-b0c6-9e3486f9fb74","urgency":0,"todoist":123}',
            sync,
            client,
        )
        task_json = json.loads(task_json)
        assert task_json['todoist'] == 123
        assert task_json['description'] == 'Test Update'
        assert feedback == 'Todoist: item updated'

    def test_on_modify_delete(self, sync, client):
        task_json, feedback = on_modify(
            '{"id":3,"description":"Test 1","entry":"20230827T232837Z","modified":"20230827T232837Z","status":"pending","uuid":"5da82ec9-e85b-47ac-b0c6-9e3486f9fb74","urgency":0,"todoist":123}',
            '{"id":3,"description":"Test 1","entry":"20230827T232837Z","modified":"20230827T233228Z","status":"deleted","uuid":"5da82ec9-e85b-47ac-b0c6-9e3486f9fb74","urgency":0,"todoist":123}',
            sync,
            client,
        )
        task_json = json.loads(task_json)
        assert feedback == 'Todoist: item deleted'

    def test_on_modify_missing(self, sync, client):
        task_json, feedback = on_modify(
            '{"id":3,"description":"Test 1","entry":"20230827T232837Z","modified":"20230827T232837Z","status":"pending","uuid":"5da82ec9-e85b-47ac-b0c6-9e3486f9fb74","urgency":0}',
            '{"id":3,"description":"Test Update","entry":"20230827T232837Z","modified":"20230827T233228Z","status":"pending","uuid":"5da82ec9-e85b-47ac-b0c6-9e3486f9fb74","urgency":0}',
            sync,
            client
        )
        task_json = json.loads(task_json)
        assert task_json['description'] == 'Test Update'
        #assert task_json['todoist'] == 123
        #assert task_json['timezone'] == 'America/New_York'
        assert feedback == 'Todoist: item added (did not exist)' 

    def test_on_modify_noop(self, sync, client):
        task_json, feedback = on_modify(
            '{"id":3,"description":"Test 1","entry":"20230827T232837Z","modified":"20230827T232837Z","status":"pending","uuid":"5da82ec9-e85b-47ac-b0c6-9e3486f9fb74","urgency":0,"todoist":123}',
            '{"id":3,"description":"Test 1","entry":"20230827T232837Z","modified":"20230828T232837Z","status":"pending","uuid":"5da82ec9-e85b-47ac-b0c6-9e3486f9fb74","urgency":0,"todoist":123}',
            sync,
            client
        )
        task_json = json.loads(task_json)
        assert feedback == 'Todoist: update not required'

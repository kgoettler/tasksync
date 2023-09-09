#!/usr/bin/env python3

import pytest

from os.path import dirname, join
import os
import datetime
import uuid

from tasksync.todoist.adapter import (
    move_item,
)
from tasksync.taskwarrior.models import TaskwarriorStatus
from tasksync.todoist.api import (
    SyncToken,
    SyncTokenManager,
    TodoistSyncDataStore,
    TodoistSyncAPI,
)
from tasksync.todoist.models import TodoistSyncTask
from tasksync.todoist.provider import TodoistProvider

from test_data import get_task

DATADIR = join(dirname(__file__), 'data')

@pytest.fixture
def store():
    return TodoistSyncDataStore(basedir=DATADIR)

@pytest.fixture
def token_manager():
    return SyncTokenManager(basedir=DATADIR)

@pytest.fixture
def provider():
    return TodoistProvider()

class TestSyncToken:

    def test_create(self):
        token = SyncToken(
            '123',
        )
        assert token.token == '123'
    
    def test_create_with_timestamp(self):
        token = SyncToken(
            '123',
            timestamp=946702800
        )
        assert token.token == '123'
        assert isinstance(token.timestamp, int)
        assert token.timestamp == 946702800

    def test_update(self):
        token = SyncToken(
            '123',
            timestamp=946702800
        )
        old_timestamp = token.timestamp
        token.update('456')
        assert token.token == '456'
        assert token.timestamp > old_timestamp

    def test_get_timestamp(self):
        # Should be within a few seconds you know
        current_time = int(datetime.datetime.now().strftime('%s'))
        token_time = SyncToken.get_timestamp()
        assert isinstance(token_time, int)
        # Should be _really_ close, but give it a few seconds to execute in case
        assert (token_time - current_time) < 5

class TestSyncTokenManager:

    def test_repr(self, token_manager):
        print(token_manager)
        assert True

    def test_get_single(self, token_manager):
        token = token_manager.get(resource_types=['projects'])
        assert isinstance(token, SyncToken)

    def test_get_multiple(self, token_manager):
        token_projects = token_manager.get(resource_types=['projects'])
        token_sections = token_manager.get(resource_types=['sections'])
        if token_sections.timestamp > token_projects.timestamp:
            token_earliest = token_projects
        else:
            token_earliest = token_sections
        token = token_manager.get(resource_types=['projects', 'sections'])
        assert isinstance(token, SyncToken)
        assert token.timestamp == token_earliest.timestamp

    def test_get_all(self, token_manager):
        token = token_manager.get()
        assert token.token == 'EARLIEST'
        assert token.timestamp == 1000000000

    def test_set_single(self, token_manager):
        value = 'set123'
        token_manager.set(value, resource_types=['projects'])
        token = token_manager.get(['projects'])
        assert isinstance(token, SyncToken)
        assert token.token == value
    
    def test_set_multiple(self, token_manager):
        value = 'set123'
        resource_types = ['projects', 'sections']
        token_manager.set(value, resource_types=resource_types)
        tokens = [token_manager.get([resource]) for resource in resource_types]
        assert all([isinstance(token, SyncToken) for token in tokens])
        assert all([token.token == value for token in tokens])
    
    def test_set_all(self, token_manager):
        value = 'set123'
        resource_types = None
        token_manager.set(value, resource_types=resource_types)
        tokens = [token_manager.get([resource]) for resource in token_manager.tokens.keys()]
        assert all([isinstance(token, SyncToken) for token in tokens])
        assert all([token.token == value for token in tokens])

    def test_save(self, token_manager):
        basedir = join(DATADIR, 'test')
        os.makedirs(basedir, exist_ok=True)
        token_manager.file = join(basedir, 'sync_tokens.json')
        token_manager.save()

        # Read it back in
        token_manager_test = SyncTokenManager(basedir)
        assert token_manager.get() == token_manager_test.get()

class TestTodoistModels:

    def test_from_todoist(self, store : TodoistSyncDataStore):
        item = TodoistSyncTask.from_todoist(store.items[-1])
        assert True


class TestTodoistProvider:

    @pytest.mark.skip()
    def test_pull(self, provider):
        res = provider.pull()
        assert True

    def test_on_add(self, provider):
        task = get_task()
        task_json, feedback = provider.on_add(task)
        assert feedback == 'Todoist: item created'
        assert len(provider.commands) == 1
    
    def test_on_modify(self, provider):
        task_old = get_task()
        task_old.project = None
        task_old.section = None
        task_new = get_task()
        task_new.description = 'This is a new description'
        task_new.project = 'Personal'
        task_new.section = 'Home'
        task_new.status = TaskwarriorStatus.COMPLETED
        task_json, feedback = provider.on_modify(task_old, task_new)
        assert feedback == 'Todoist: item updated, moved, and completed'
    
    def test_on_modify_delete(self, provider):
        task_old = get_task()
        task_new = get_task()
        task_new.description = 'This is a new description'
        task_new.status = TaskwarriorStatus.DELETED
        task_json, feedback = provider.on_modify(task_old, task_new)
        assert feedback == 'Todoist: item updated and deleted'
    
    def test_on_modify_uncomplete(self, provider):
        task_old = get_task()
        task_old.status = TaskwarriorStatus.COMPLETED
        task_new = get_task()
        task_new.status = TaskwarriorStatus.PENDING
        task_json, feedback = provider.on_modify(task_old, task_new)
        assert feedback == 'Todoist: item uncompleted'
    
    def test_on_modify_noop(self, provider):
        task_old = get_task()
        task_new = get_task()
        task_json, feedback = provider.on_modify(task_old, task_new)
        assert feedback == 'Todoist: update not required'


class TestTodoistAdapter:

    def test_move_project_00(self, store):
        task_old= get_task()
        task_old.project = None
        task_new = get_task()
        task_new.project = None
        
        ops = move_item(task_old, task_new, store)
        assert ops[0]['args']['project_id'] == '1000000000'

    def test_move_project_01(self, store):
        task_old= get_task()
        task_old.project = None
        task_new = get_task()
        task_new.project = 'Personal'

        ops = move_item(task_old, task_new, store)
        assert ops[0]['args']['project_id'] == '1000000001'

    def test_move_project_10(self, store):
        task_old = get_task()
        task_old.project = 'Personal'
        task_new = get_task()
        task_new.project = None

        ops = move_item(task_old, task_new, store)
        assert ops[0]['args']['project_id'] == '1000000000'

    def test_move_project_11(self, store):
        task_old = get_task()
        task_old.project = 'Inbox'
        task_new = get_task()
        task_new.project = 'Personal'

        ops = move_item(task_old, task_new, store)
        assert ops[0]['args']['project_id'] == '1000000001'
    
    def test_move_project_noop(self, store):
        task_old = get_task()
        task_old.project = 'Personal'
        task_new = get_task()
        task_new.project = 'Personal'

        ops = move_item(task_old, task_new, store)
        assert len(ops) == 0

    def test_move_to_section_within_project(self, store):
        task_old = get_task()
        task_old.project = 'Inbox'
        task_old.section = None
        task_new = get_task()
        task_new.project = 'Inbox'
        task_new.section = 'Recents'

        ops = move_item(task_old, task_new, store)
        assert 'project_id' not in ops[0]['args']
        assert ops[0]['args']['section_id'] == '100000000'

    def test_move_from_section_within_project(self, store):
        task_old = get_task()
        task_old.project = 'Inbox'
        task_old.section = 'Recents'
        task_new = get_task()
        task_new.project = 'Inbox'
        task_new.section = None

        ops = move_item(task_old, task_new, store)
        assert 'section_id' not in ops[0]['args']
        assert ops[0]['args']['project_id'] == '1000000000'

    def test_move_to_section_new(self, store):
        task_old = get_task()
        task_old.project = 'Inbox'
        task_old.section = None
        task_new = get_task()
        task_new.project = 'Inbox'
        task_new.section = 'New Section'

        ops = move_item(task_old, task_new, store)
        assert len(ops) == 2
        assert ops[0]['type'] == 'section_add'
        assert ops[1]['type'] == 'item_move'
        assert ops[0]['temp_id'] == ops[1]['args']['section_id']


class TestTodoistSyncAPI:

    def test_create_project_helper(self):
        kwargs = dict(
            name='Test Project',
            temp_id=str(uuid.uuid4()),
            color='#FF0000',
            parent_id='123',
            child_order=1,
            is_favorite=True,
            view_style='foo',
        )
        data = TodoistSyncAPI.create_project(**kwargs) # type: ignore

        assert data['type'] == 'project_add'
        assert uuid.UUID(data['uuid'])
        for key, value in kwargs.items():
            assert data['args'][key] == value
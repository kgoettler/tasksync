#!/usr/bin/env python3

import pytest

from os.path import dirname, join
import os
import datetime

from tasksync.todoist.api import SyncToken, SyncTokenManager, TodoistSyncDataStore
from tasksync.todoist.models import TodoistSyncTask
from tasksync.todoist.provider import TodoistProvider

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

    def test_write(self, token_manager):
        basedir = join(DATADIR, 'test')
        os.makedirs(basedir, exist_ok=True)
        token_manager.file = join(basedir, 'sync_tokens.json')
        token_manager.write()

        # Read it back in
        token_manager_test = SyncTokenManager(basedir)
        assert token_manager.get() == token_manager_test.get()

class TestTodoistModels:

    def test_from_todoist(self, store : TodoistSyncDataStore):
        item = TodoistSyncTask.from_todoist(store.items[-1])
        assert True


class TestTodoistProvider:

    def test_pull(self, provider):
        res = provider.pull()
        assert True
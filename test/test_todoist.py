#!/usr/bin/env python3

import pytest

from os.path import dirname, join
import os
import datetime

from tasksync.todoist import TodoistSyncDataStore, TodoistSyncTask

DATADIR = join(dirname(__file__), 'data')

@pytest.fixture
def store():
    return TodoistSyncDataStore(basedir=DATADIR)

class TestTodoistSyncTask:

    def test_from_todoist(self, store : TodoistSyncDataStore):
        item = TodoistSyncTask.from_todoist(store.items[-1])
        assert True
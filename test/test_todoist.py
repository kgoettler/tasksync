#!/usr/bin/env python3

import datetime

import pytest

from todoist_api_python.models import Task as TodoistTask, Due as TodoistDue
from tasksync.todoist import SyncToken, SyncTokenManager

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

#!/usr/bin/env python3
import pytest

import os
import subprocess

CLI_PATH = os.path.join(os.path.dirname(__file__), '..', 'cli.py')

def call_tasksync(*args):
    return subprocess.run([
            'python3',
            CLI_PATH,
            *args,
        ],
        capture_output=True,
    )

@pytest.fixture()
def tasksync_running():
    res = call_tasksync('start')
    yield res
    res = call_tasksync('stop')

class TestCLI:

    def test_noop(self):
        res = call_tasksync()
        assert res.returncode == 0
        assert res.stdout[0:5] == b'usage'
    
    def test_status_not_running(self):
        res = call_tasksync('status')
        assert res.returncode == 1
        assert res.stdout.startswith(b'tasksync is not running')

    def test_stop_not_running(self):
        res = call_tasksync('stop')
        assert res.returncode == 1
        assert res.stdout.startswith(b'tasksync is not running')

    def test_version(self):
        res = call_tasksync('-v')
        assert res.returncode == 0

    def test_running(self):
        res = call_tasksync('start')
        res = call_tasksync('status')
        assert res.returncode == 0
        assert res.stdout.startswith(b'tasksync is running with pid')
        res = call_tasksync('start')
        assert res.returncode == 1
        assert res.stdout.startswith(b'tasksync is already running')
        res = call_tasksync('stop')
        assert res.returncode == 0
        assert res.stdout.startswith(b'tasksync stopped')
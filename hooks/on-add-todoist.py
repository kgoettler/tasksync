#!/Users/kgoettler/miniforge3/envs/main/bin/python3

import traceback
import sys
import os

from tasksync.hooks import on_add
from tasksync.server.client import TasksyncClient
from tasksync.todoist.provider import TodoistProvider

# Read TaskWarrior task from stdin
task_str = sys.stdin.readline()

try:
    client = TasksyncClient()
    client.connect()
    feedback = client.on_add(task_str)
    client.close()
except ConnectionRefusedError:
    print(task_str)
    print('Unable to connect to tasksync server - is it running?')
    sys.exit(1)
except Exception as e:
    print(task_str)
    print(traceback.format_exc())
    sys.exit(100)

print(task_str)
if len(feedback) > 0:
    print(feedback)
sys.exit(0)

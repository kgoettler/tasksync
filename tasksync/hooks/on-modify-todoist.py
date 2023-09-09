#!/usr/bin/env python3

import traceback
import sys

from tasksync.server.client import TasksyncClient

# Read TaskWarrior task from stdin
task_str_old = sys.stdin.readline()
task_str_new = sys.stdin.readline()

try:
    client = TasksyncClient()
    client.connect()
    feedback = client.on_modify(task_str_old, task_str_new)
    client.close()
except ConnectionRefusedError:
    print(task_str_old)
    print("Unable to connect to tasksync server - is it running?")
    sys.exit(1)
except Exception as e:
    print(task_str_new)
    print(traceback.format_exc())
    sys.exit(100)

print(task_str_new)
if len(feedback) > 0:
    print(feedback)
sys.exit(0)

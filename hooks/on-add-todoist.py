#!/Users/kgoettler/miniforge3/envs/main/bin/python3

import traceback
import sys
import os

from tasksync.hooks import on_add
from tasksync.server import TasksyncClient
from tasksync.todoist import TodoistSync

# Read TaskWarrior task from stdin
task_json_input = sys.stdin.readline()

try:
    sync = TodoistSync(basedir=os.path.join(os.environ['HOME'], '.todoist'))
    client = TasksyncClient()
    task_json_input, feedback = on_add(task_json_input, sync, client)
except Exception as e:
    print(task_json_input)
    print(traceback.format_exc())
    sys.exit(1)

print(task_json_input)
if len(feedback) > 0:
    print(feedback)
sys.exit(0)

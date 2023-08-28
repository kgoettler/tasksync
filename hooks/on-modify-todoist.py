#!/Users/kgoettler/miniforge3/envs/main/bin/python3

import traceback
import sys
import re
import json
import os
import requests
from datetime import datetime

from tasksync.hooks import on_modify
from tasksync.models import TaskwarriorTask, TaskwarriorDatetime
from todoist_api_python.api import TodoistAPI
import tzlocal

# Read TaskWarrior task from stdin
task_json_input = sys.stdin.readline()
task_json_output = sys.stdin.readline()

try:
    api = TodoistAPI(os.environ['TODOIST_API_KEY'])
    task_json_output, feedback = on_modify(task_json_input, task_json_output, api)
except Exception as e:
    print(task_json_output)
    print(traceback.format_exc())
    sys.exit(1)

print(task_json_output)
if len(feedback) > 0:
    print(feedback)
sys.exit(0)

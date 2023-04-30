#!/Users/kgoettler/miniforge3/envs/main/bin/python3

import sys
import re
import json
import os
from datetime import datetime

from todoist_api_python.api import TodoistAPI
import tzlocal

WORK_PROJECT_ID = '2299975668'
TASKWARRIOR_DATETIME_FORMAT = '%Y%m%dT%H%M%SZ'

# Read TaskWarrior task from stdin
added_task = json.loads(sys.stdin.readline())

# Create payload for Todoist task
data = {
    'content': added_task['description'],
    'project_id': WORK_PROJECT_ID,
}
if 'due' in added_task:
    data['due_date'] = datetime.strptime(added_task['due'], TASKWARRIOR_DATETIME_FORMAT).strftime('%Y-%m-%d')
api = TodoistAPI(os.environ['TODOIST_API_KEY'])
res = api.add_task(**data)

# Add Todoist task ID to TaskWarrior task
added_task['todoist'] = str(res.id)
added_task['tz'] = tzlocal.get_localzone_name()

print(json.dumps(added_task))

sys.exit(0)

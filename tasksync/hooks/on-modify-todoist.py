#!/Users/kgoettler/miniforge3/envs/main/bin/python3

import sys
import re
import json
import os

from todoist_api_python.api import TodoistAPI
import tzlocal

WORK_PROJECT_ID = '2299975668'
TASKWARRIOR_DATETIME_FORMAT = '%Y%m%dT%H%M%SZ'
TODOIST_DATETIME_FORMATS = [
    '%Y-%m-%d',
    '%Y-%m-%dT%H:%M:%S',
    '%Y-%m-%dT%H:%M:%SZ',
]
api = TodoistAPI(os.environ['TODOIST_API_KEY'])

# Read TaskWarrior tasks from stdin
task_old = json.loads(sys.stdin.readline())
task_new = json.loads(sys.stdin.readline())

# Check to see if any Todoist-relevant changes were made
args = {
    'task_id': str(int(task_new['todoist'])),
}
feedback = ''

if task_new['status'] == 'deleted':
    try:
        api.delete_task(**args)
    except Exception as error:
        feedback = str(error)
else:
    # Handle due date change
    if task_old.get('due', None) != task_new.get('due', None):
        due_datetime = (datetime
            .strptime(task_old['due'], TASKWARRIOR_DATETIME_FORMAT)
            .strftime(TODOIST_DATETIME_FORMATS[0] if due_date.hour == 4 else TODOIST_DATETIME_FORMATS[-1])
        )
        args['due_datetime'] = due_datetime
        # Save current timezone on task
        task_new['tz'] = tzinfo.get_localzone_name()
    # Handle description change
    if task_old['description'] != task_new['description']:
        args['content'] = task_new['description']
    if len(args) > 1:
        try:
            res = api.update_task(**args)
        except Exception as error:
            feedback = str(error)

print(json.dumps(task_new))

if len(feedback) > 0:
    print(feedback)

sys.exit(0)

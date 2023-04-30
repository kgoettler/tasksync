from datetime import datetime
from enum import Enum
import re

from zoneinfo import ZoneInfo
import tzlocal

WORK_PROJECT_ID = '2299975668'
TASKWARRIOR_DATETIME_FORMAT = '%Y%m%dT%H%M%SZ'
TODOIST_DATETIME_FORMATS = [
    '%Y-%m-%d',
    '%Y-%m-%dT%H:%M:%S',
    '%Y-%m-%dT%H:%M:%SZ',
]

def todoist_get_task_map(todo_data, by='id'):
    return {str(int(item[by])):item for item in todo_data['items'] if item['project_id'] == WORK_PROJECT_ID}

def todoist_get_section_map(todo_data, by='name'):
    return {item[by]:item for item in todo_data['sections'] if item['project_id'] == WORK_PROJECT_ID}

def convert_todoist_task(task, sections=[]):
    '''
    Convert Todoist task into TaskWarrior task
    '''
    out = {
        'description': task['content'],
        'todoist': str(int(task['id'])),
    }
    if 'due' in task and task['due'] is not None:
        due = parse_todoist_date(task['due'])
        out['due'] = due.astimezone(ZoneInfo('UTC')).strftime(TASKWARRIOR_DATETIME_FORMAT)
    for section in sections:
        if section['id'] == task['section_id']:
            out['project'] = section['name']
            break
    return out

def convert_taskwarrior_task(task):
    '''
    Convert TaskWarrior task into Todoist task
    '''
    out = {
        'content': task['description'],
    }
    if task.get('todoist', None) is not None:
        out['id'] = task['todoist']
    if 'due' in task:
        due_date = parse_taskwarrior_date(task['due'], tzstr=task.get('tz'))
        if due_date.hour == 0 and due_date.minute == 0 and due_date.second == 0:
            out['due'] = {'date': due_date.strftime('%Y-%m-%d')}
        else:
            out['due'] = {'date': due_date.strftime('%Y-%m-%dT%H:%M:%S')}
        # If due date is 4AM UTC, it's midnight in EST
        # -> no explicit time set on due date
        # -> don't push an explicit time to todoist
        #due_date = parse_taskwarrior_date(task['due'], tzstr=task.get('tz'))
        #out['due'] = {
        #    'date': due_date #.strftime(TODOIST_DATETIME_FORMATS[0] if due_date.hour == 4 else TODOIST_DATETIME_FORMATS[-1])
        #}
    return out

def parse_todoist_date(datedict):
    d = None
    # Check if this is a simple datestr (e.g. YYYY-mm-dd)
    try:
        d = datetime.strptime(datedict['date'], TODOIST_DATETIME_FORMATS[0])
        d = d.replace(tzinfo=tzlocal.get_localzone().unwrap_shim())
    except:
        pass
    # Check if this is a "floating" date
    if d is None:
        try:
            d = datetime.strptime(datedict['date'], TODOIST_DATETIME_FORMATS[1])
            d = d.replace(tzinfo=tzlocal.get_localzone().unwrap_shim())
        except:
            pass
    # This *must* be a timezone aware datetime
    if d is None:
        d = datetime.strptime(datedict['date'], TODOIST_DATETIME_FORMATS[2])
        # All Todoist datetimes are stored in UTC, so add this to the object
        d = d.replace(tzinfo=ZoneInfo('UTC'))
    return d

def parse_todoist_date_string(datestr):
    date = None
    for fmt in TODOIST_DATETIME_FORMATS:
        try:
            date = datetime.strptime(datestr, fmt)
        except:
            pass
    return date

def parse_taskwarrior_date_string(datestr):
    date = None
    try:
        date = datetime.strptime(datestr, TASKWARRIOR_DATETIME_FORMAT)
        # All TaskWarrior datetimes are stored in UTC, so add this to the datetime object
        date = date.replace(tzinfo=ZoneInfo('UTC'))
    except:
        pass
    return date

def parse_taskwarrior_date(datestr, tzstr=None):
    d = parse_taskwarrior_date_string(datestr)
    if tzstr is not None:
        d = d.astimezone(ZoneInfo(tzstr))
    return d
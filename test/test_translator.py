import pytest
from os.path import dirname, join
import uuid

from tasksync.taskwarrior import TaskwarriorDatetime, TaskwarriorPriority, TaskwarriorStatus, TaskwarriorTask
from tasksync.todoist import TodoistSyncDataStore
from tasksync.translator import (
    add_item,
    update_item,
    move_item,
    delete_item,
    complete_item,
    uncomplete_item,
    create_project,
    date_from_taskwarrior,
    TODOIST_DATETIME_FORMAT
)

from test_data import get_task

@pytest.fixture
def task():
    return get_task()

@pytest.fixture
def old_task():
    return get_task()

@pytest.fixture
def new_task():
    return get_task()

@pytest.fixture
def store():
    return TodoistSyncDataStore(basedir=join(dirname(__file__), 'data'))

def test_add_item(task, store):
    task.project = 'Inbox'
    ops = add_item(task, store)
    assert len(ops) == 1
    op = ops[0]
    assert op['type'] == 'item_add'
    assert uuid.UUID(op['temp_id'])
    assert uuid.UUID(op['uuid'])
    assert op['args']['content'] == 'Test case w/ due_date'
    assert op['args']['due']['date'] == '2023-08-28'
    assert op['args']['due']['is_recurring'] is False
    assert op['args']['due']['timezone'] == 'America/New_York'
    assert len(op['args']['labels']) == 1
    assert op['args']['labels'][0] == 'test2'

def test_update_item_content(old_task, new_task, store):
    new_task.description = 'Changed'
    ops = update_item(old_task, new_task, store)

    assert len(ops) == 1
    op = ops[0]
    assert op['type'] == 'item_update'
    assert uuid.UUID(op['uuid'])
    assert op['args']['id'] == str(new_task.todoist)
    assert op['args']['content'] == new_task.description

def test_update_item_update_due(old_task, new_task, store):
    new_task.due = TaskwarriorDatetime.now()
    ops = update_item(old_task, new_task, store)

    assert len(ops) == 1
    op = ops[0]
    assert op['type'] == 'item_update'
    assert uuid.UUID(op['uuid'])
    assert op['args']['id'] == str(new_task.todoist)
    assert op['args']['due']['timezone'] == new_task.timezone
    assert op['args']['due']['is_recurring'] is False
    assert op['args']['due']['date'] == new_task.due.strftime(TODOIST_DATETIME_FORMAT)

def test_update_item_remove_due(old_task, new_task, store):
    new_task.due = None
    ops = update_item(old_task, new_task, store)

    assert len(ops) == 1
    op = ops[0]
    assert op['type'] == 'item_update'
    assert uuid.UUID(op['uuid'])
    assert op['args']['id'] == str(new_task.todoist)
    assert op['args']['due'] is None

def test_update_item_update_priority(old_task, new_task, store):
    new_task.priority = TaskwarriorPriority['H']
    ops = update_item(old_task, new_task, store)

    assert len(ops) == 1
    op = ops[0]
    assert op['type'] == 'item_update'
    assert uuid.UUID(op['uuid'])
    assert op['args']['id'] == str(new_task.todoist)
    assert op['args']['priority'] == 4

def test_update_item_remove_priority(old_task, new_task, store):
    old_task.priority = TaskwarriorPriority['H']
    new_task.priority = None
    ops = update_item(old_task, new_task, store)

    assert len(ops) == 1
    op = ops[0]
    assert op['type'] == 'item_update'
    assert uuid.UUID(op['uuid'])
    assert op['args']['id'] == str(new_task.todoist)
    assert op['args']['priority'] == 1

def test_update_item_update_labels(old_task, new_task, store):
    new_task.tags.append('Another Tag')
    ops = update_item(old_task, new_task, store)

    assert len(ops) == 1
    op = ops[0]
    assert op['type'] == 'item_update'
    assert uuid.UUID(op['uuid'])
    assert op['args']['id'] == str(new_task.todoist)
    assert len(op['args']['labels']) == 2
    assert op['args']['labels'][-1] == new_task.tags[-1]

def test_update_item_remove_labels(old_task, new_task, store):
    new_task.tags = []
    ops = update_item(old_task, new_task, store)

    assert len(ops) == 1
    op = ops[0]
    assert op['type'] == 'item_update'
    assert uuid.UUID(op['uuid'])
    assert op['args']['id'] == str(new_task.todoist)
    assert len(op['args']['labels']) == 0

def test_update_item_all(old_task, new_task, store):
    new_task.description = 'Changed'
    new_task.due = TaskwarriorDatetime.now()
    new_task.priority = TaskwarriorPriority['H']
    new_task.tags.append('Another Tag')
    ops = update_item(old_task, new_task, store)

    assert len(ops) == 1
    op = ops[0]
    assert op['type'] == 'item_update'
    assert uuid.UUID(op['uuid'])
    assert op['args']['id'] == str(new_task.todoist)
    assert op['args']['content'] == new_task.description
    assert op['args']['due']['timezone'] == new_task.timezone
    assert op['args']['due']['is_recurring'] is False
    assert op['args']['due']['date'] == new_task.due.strftime(TODOIST_DATETIME_FORMAT)
    assert op['args']['priority'] == 4
    assert len(op['args']['labels']) == 2
    assert op['args']['labels'][-1] == new_task.tags[-1]

def test_move_item_existing_project(old_task, new_task, store):
    old_task.project = 'Inbox'
    new_task.project = 'Personal'
    ops = move_item(old_task, new_task, store)
    
    assert len(ops) == 1
    op = ops[0]
    assert op['type'] == 'item_move'
    assert uuid.UUID(op['uuid'])
    assert op['args']['id'] == str(new_task.todoist)
    assert op['args']['project_id'] == store.find('projects', name='Personal')['id']

def test_move_item_new_project(old_task, new_task, store):
    old_task.project = 'Inbox'
    new_task.project = 'Work'
    
    ops = move_item(old_task, new_task, store)
    
    assert len(ops) == 2
    op = ops[0]
    assert op['type'] == 'project_add'
    assert uuid.UUID(op['uuid'])
    assert uuid.UUID(op['temp_id'])
    assert op['args']['name'] == 'Work'

    op = ops[1]
    assert op['type'] == 'item_move'
    assert uuid.UUID(op['uuid'])
    assert op['args']['id'] == str(new_task.todoist)
    assert op['args']['project_id'] == ops[0]['temp_id']

def test_move_item_no_project(old_task, new_task, store):
    old_task.project = 'Personal'
    new_task.project = None
    
    ops = move_item(old_task, new_task, store)

    assert len(ops) == 1    
    op = ops[0]
    assert op['type'] == 'item_move'
    assert uuid.UUID(op['uuid'])
    assert op['args']['id'] == str(new_task.todoist)
    assert op['args']['project_id'] == store.find('projects', name='Inbox')['id']

def test_move_item_no_inbox(old_task, new_task, store : TodoistSyncDataStore):
    store.projects = []
    old_task.project = 'Personal'
    new_task.project = None
    with pytest.raises(RuntimeError):    
        ops = move_item(old_task, new_task, store)

def test_delete_item(old_task : TaskwarriorTask, new_task : TaskwarriorTask, store : TodoistSyncDataStore):
    old_task.status = TaskwarriorStatus.PENDING
    new_task.status = TaskwarriorStatus.DELETED
    ops = delete_item(old_task, new_task, store)

    assert len(ops) == 1    
    op = ops[0]
    assert op['type'] == 'item_delete'
    assert uuid.UUID(op['uuid'])
    assert op['args']['id'] == str(new_task.todoist)

def test_complete_item(old_task : TaskwarriorTask, new_task : TaskwarriorTask, store : TodoistSyncDataStore):
    old_task.status = TaskwarriorStatus.PENDING
    new_task.status = TaskwarriorStatus.COMPLETED
    new_task.end = TaskwarriorDatetime.now()
    ops = complete_item(old_task, new_task, store)

    assert len(ops) == 1    
    op = ops[0]
    assert op['type'] == 'item_complete'
    assert uuid.UUID(op['uuid'])
    assert op['args']['id'] == str(new_task.todoist)

def test_uncomplete_item(old_task : TaskwarriorTask, new_task : TaskwarriorTask, store : TodoistSyncDataStore):
    old_task.status = TaskwarriorStatus.COMPLETED
    new_task.status = TaskwarriorStatus.PENDING
    ops = uncomplete_item(old_task, new_task, store)

    assert len(ops) == 1    
    op = ops[0]
    assert op['type'] == 'item_uncomplete'
    assert uuid.UUID(op['uuid'])
    assert op['args']['id'] == str(new_task.todoist)


def test_create_project_helper():
    kwargs = dict(
        name='Test Project',
        color='#FF0000',
        parent_id='123',
        child_order=1,
        is_favorite=True,
        view_style='foo',
    )
    ops = create_project(**kwargs) # type: ignore

    assert len(ops) == 1
    op = ops[0]
    assert op['type'] == 'project_add'
    assert uuid.UUID(op['uuid'])
    for key, value in kwargs.items():
        assert op['args'][key] == value

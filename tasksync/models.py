import datetime
import json
import uuid
from enum import Enum
from dataclasses import dataclass
from typing import Optional

from todoist_api_python.models import Task, Due
from zoneinfo import ZoneInfo
import tzlocal

TODOIST_DUE_DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
TODOIST_DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'

class TaskwarriorStatus(Enum):
    DELETED = 0
    COMPLETED = 1
    PENDING = 2
    WAITING = 3
    RECURRING = 4

    def __str__(self) -> str:
        return self.name.lower()

class TaskwarriorPriority(Enum):
    H = 3
    M = 2
    L = 1

    def __str__(self) -> str:
        return self.name
    
    @classmethod
    def from_todoist(cls, value):
        # Todoist priorities differ by 1
        return cls(value-1)
    
    def to_todoist(self):
        return self.value + 1

class TaskwarriorDatetime(datetime.datetime):
    
    def __str__(self) -> str:
        # TODO: need this to be timezone aware?
        return self.strftime('%Y%m%dT%H%M%SZ')
    
    @classmethod
    def from_taskwarrior(cls, value):
        return cls.strptime(value, '%Y%m%dT%H%M%SZ').replace(tzinfo=ZoneInfo('UTC'))

    @classmethod 
    def from_todoist(cls, value):
        if isinstance(value, Due):
            if value.datetime is not None:
                return (cls
                        .strptime(value.datetime, TODOIST_DUE_DATETIME_FORMAT)
                        .replace(tzinfo=ZoneInfo('UTC'))
                )
            else:
                return (cls
                        .strptime(value.date, '%Y-%m-%d')
                        .replace(tzinfo=tzlocal.get_localzone().unwrap_shim())
                        .astimezone(ZoneInfo('UTC'))
                )
        elif isinstance(value, str):
            return cls.strptime(value, TODOIST_DATETIME_FORMAT)
        

@dataclass
class TaskwarriorTask:
    description: str
    uuid : uuid.UUID
    entry : TaskwarriorDatetime = TaskwarriorDatetime.now()
    status : TaskwarriorStatus = TaskwarriorStatus.PENDING
    id : Optional[int] = None
    start : Optional[TaskwarriorDatetime] = None
    end :  Optional[TaskwarriorDatetime] = None
    due : Optional[TaskwarriorDatetime] = None
    until : Optional[TaskwarriorDatetime] = None 
    wait : Optional[TaskwarriorDatetime] = None
    modified: Optional[TaskwarriorDatetime] = None
    project : Optional[str] = None
    tags : list[str] = ()
    priority: Optional[TaskwarriorPriority] = None
    urgency : int = 1
    
    # UDAs
    todoist : Optional[int] = None
    timezone : Optional[str] = tzlocal.get_localzone_name()

    @classmethod
    def from_taskwarrior(cls, data):
        kwargs = {
            'description': data['description'],
            'uuid': data['uuid'],
            'entry': TaskwarriorDatetime.from_taskwarrior(data['entry']),
            'status': TaskwarriorStatus[data['status'].upper()],
        }
        # Optional includes
        for key in ['project', 'tags', 'urgency']:
            if key in data:
                kwargs[key] = data[key]
        # Cast ints
        for key in ['id', 'todoist']:
            if key in data:
                kwargs[key] = int(data[key])
        # Cast datetimes
        for key in ['start', 'end', 'due', 'until', 'wait',' modified']:
            if key in data:
                kwargs[key] = TaskwarriorDatetime.from_taskwarrior(data[key])
        # Cast priority
        if 'priority' in data:
            kwargs['priority'] = TaskwarriorPriority[data['priority']]
        return cls(**kwargs)

    @classmethod
    def from_todoist(cls, task):
        kwargs = dict(
            uuid=uuid.uuid4(),
            description=task.content,
            entry=TaskwarriorDatetime.from_todoist(task.created_at),
            status=TaskwarriorStatus.COMPLETED if task.is_completed else TaskwarriorStatus.PENDING,
        )
        if task.due is not None:
            # TODO: Support datetimes
            kwargs['due'] = TaskwarriorDatetime.from_todoist(task.due)
        if task.project_id != 'Inbox':
            kwargs['project'] = task.project_id
        if len(task.labels) > 0:
            kwargs['tags'] = task.labels
        if task.priority > 1:
            kwargs['priority'] = TaskwarriorPriority.from_todoist(task.priority)
        kwargs['todoist'] = int(task.id)
        return cls(**kwargs)
    
    def update(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        return

    def to_dict(self, exclude_id=False) -> dict:
        out = {}
        if not exclude_id:
            out['id'] = self.id
        for attr in ['description', 'uuid', 'entry', 'status', 'start', 'end', 'due', 'until', 'wait', 'project', 'priority']:
            value = getattr(self, attr)
            if value is not None:
                out[attr] = str(value)
        for attr in ['urgency', 'todoist', 'timezone']:
            value = getattr(self, attr)
            if value is not None:
                out[attr] = value
        if len(self.tags) > 0:
            out['tags'] = self.tags
        return out
    
    def to_json(self, exclude_id=False, **kwargs) -> str:
        return json.dumps(self.to_dict(exclude_id=exclude_id), **kwargs)
    
    def to_todoist_api_kwargs(self) -> dict:
        kwargs = {}
        if self.todoist:
            kwargs['task_id'] = str(self.todoist)
        kwargs['content'] = self.description
        kwargs['is_completed'] = self.status == TaskwarriorStatus.COMPLETED
        if len(self.tags) > 0:
            kwargs['labels'] = self.tags
        if self.priority:
            kwargs['priority'] = self.priority.to_todoist()
        if self.due:
            key, value = parse_todoist_due_datetime(self.due, self.timezone)
            kwargs[key] = value
        return kwargs
    
def parse_todoist_due_datetime(due : TaskwarriorDatetime, timezone : str) -> tuple[str, str]:
    # Convert TaskwarriorDatetime to local timezone
    due_datetime = due.astimezone(ZoneInfo(timezone))
    if due_datetime.hour == 0 and due_datetime.minute == 0:
        return 'due_date', due.strftime('%Y-%m-%d')
    else:
        return 'due_datetime', due.strftime(TODOIST_DATETIME_FORMAT)
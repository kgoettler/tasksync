import datetime
import json
import uuid
from enum import Enum
from dataclasses import dataclass
from typing import Optional

from todoist_api_python.models import Task, Due

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
    def from_str(cls, value):
        if value not in cls.__members__:
            raise ValueError('\'{}\' is not a valid str value for {}'.format(
                value,
                cls.__name__,
            ))
        return cls[value]

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
        return cls.strptime(value, '%Y%m%dT%H%M%SZ')

    @classmethod 
    def from_todoist(cls, value):
        if isinstance(value, Due):
            return cls.now()
        elif isinstance(value, str):
            return cls.strptime(value, '%Y-%m-%dT%H:%M:%S.%fZ')
        

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
    todoist : Optional[int] = None

    @classmethod
    def from_taskwarrior(cls, data):
        kwargs = {
            'description': data['description'],
            'uuid': data['uuid'],
            'entry': TaskwarriorDatetime.from_taskwarrior(data['entry']),
            'status': TaskwarriorStatus[data['status'].upper()],
        }
        # Optional includes
        for key in ['project', 'tags', 'urgency', 'todoist']:
            if key in data:
                kwargs[key] = data[key]
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
            description=task.content,
            entry=TaskwarriorDatetime.from_todoist(task.created_at),
            status=TaskwarriorStatus.COMPLETED if task.is_completed else TaskwarriorStatus.PENDING,
        )
        if task.due is not None:
            # TODO: Support datetimes
            kwargs['due'] = TaskwarriorDatetime.strptime(task.due.date,)
        if task.project_id != 'Inbox':
            kwargs['project'] = task.project_id
        if len(task.labels) > 0:
            kwargs['tags'] = task.labels
        if task.priority > 1:
            kwargs['priority'] = TaskwarriorPriority.from_todoist(task.priority)
        kwargs['todoist'] = int(task.id)
        return cls(**kwargs)
    
    def update(self, data: dict):
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
        return

    def to_dict(self) -> dict:
        out = {
            'id': self.id,
            'description': self.description,
            'uuid': str(self.uuid),
            'entry': str(self.entry),
            'status': str(self.status),
            'urgency': self.urgency,
        }
        for attr in ['start', 'end', 'due', 'until', 'wait', 'project', 'priority']:
            if value := getattr(self, attr):
                if value is not None:
                    out[attr] = str(value)
        if self.todoist is not None:
            out['todoist'] = self.todoist
        if len(self.tags) > 0:
            out['tags'] = self.tags
        return out
    
    def to_json(self, **kwargs) -> str:
        return json.dumps(self.to_dict(), **kwargs)
    
    def to_todoist_api_kwargs(self) -> dict:
        kwargs = {}
        if self.todoist:
            kwargs['task_id'] = self.todoist
        kwargs['content'] = self.description
        kwargs['is_completed'] = self.status == TaskwarriorStatus.COMPLETED
        if len(self.tags) > 0:
            kwargs['labels'] = self.tags
        if self.priority:
            kwargs['priority'] = self.priority.to_todoist()
        return kwargs
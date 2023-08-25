#!/usr/bin/env python3

import datetime
import json
import uuid
from enum import Enum
from dataclasses import dataclass
from typing import Optional

@dataclass
class TodoistDate:
    string: str
    date : str
    is_recurring : bool
    datetime : str
    timezone : str

@dataclass
class TodoistDuration:
    amount : int
    unit : str

@dataclass
class TodoistTask:
    id : str
    project_id : str
    section_id : str
    content : str
    description : str
    is_completed : bool
    labels : list[str]
    parent_id : str
    order : int
    priority : int
    due : TodoistDate
    url : str
    comment_count : int
    created_at : str
    creator_id : str
    assignee_id : str
    assigner_id : str
    duration : TodoistDuration

class TaskwarriorStatus(Enum):
    DELETED = 0
    COMPLETED = 1
    PENDING = 2
    WAITING = 3
    RECURRING = 4

    def __str__(self):
        return self.name.lower()


class TaskwarriorDatetime(datetime.datetime):
    
    def __str__(self):
        # TODO: need this to be timezone aware?
        return self.strftime('%Y%m%dT%H%M%SZ')


class TaskwarriorPriority(Enum):
    H = 3
    M = 2
    L = 1

@dataclass
class TaskwarriorTask:
    id : int
    description: str
    uuid : uuid.UUID
    entry : TaskwarriorDatetime = TaskwarriorDatetime.now()
    status : TaskwarriorStatus = TaskwarriorStatus.PENDING
    start : Optional[TaskwarriorDatetime] = None
    end :  Optional[TaskwarriorDatetime] = None
    due : Optional[TaskwarriorDatetime] = None
    until : Optional[TaskwarriorDatetime] = None 
    wait : Optional[TaskwarriorDatetime] = None
    project : Optional[str] = None
    tags : list[str] = ()
    priority: Optional[TaskwarriorPriority] = None
    urgency : int = 1

    @classmethod
    def new(cls, description, **kwargs):
        return TaskwarriorTask(
            id=1,
            description=description,
            uuid=uuid.uuid4(),
            entry=TaskwarriorDatetime.now(),
            **kwargs,
        )

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
            if value := getattr(self, attr) != None:
                out[attr] = value
        if len(self.tags) > 0:
            out['tags'] = self.tags
        return out
    
    def to_json(self, **kwargs) -> str:
        return json.dumps(self.to_dict(), **kwargs)


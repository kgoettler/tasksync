from __future__ import annotations

import datetime
import json
import uuid
from enum import Enum
from dataclasses import dataclass, field
from typing import Union, TypedDict

from zoneinfo import ZoneInfo

class TaskwarriorStatus(Enum):
    '''Enum for storing Taskwarrior task status'''
    DELETED = 0
    COMPLETED = 1
    PENDING = 2
    WAITING = 3
    RECURRING = 4

    def __str__(self) -> str:
        return self.name.lower()

class TaskwarriorPriority(Enum):
    '''Enum for storing Taskwarrior priorities'''
    H = 3
    M = 2
    L = 1

    def __str__(self) -> str:
        return self.name
    
class TaskwarriorDatetime(datetime.datetime):
    '''Class for storing Taskwarrior datetime values'''
    
    def __str__(self) -> str:
        # TODO: need this to be timezone aware?
        return self.strftime('%Y%m%dT%H%M%SZ')
    
    @classmethod
    def from_taskwarrior(cls, value):
        return cls.strptime(value, '%Y%m%dT%H%M%SZ').replace(tzinfo=ZoneInfo('UTC'))

class TaskwarriorDict(TypedDict):
    description : str
    uuid : str
    description: str
    uuid : str
    entry : str
    status : str
    id : int
    start : str
    end : str
    due : str
    until : str
    wait : str
    modified: str
    project : str
    tags : list[str]
    priority: str
    urgency : float
    # UDAs
    section : str
    todoist : int
    timezone : str

@dataclass
class TaskwarriorTask:
    '''Dataclass for a single Taskwarrior task'''
    description: str
    uuid : uuid.UUID
    entry : TaskwarriorDatetime | None = TaskwarriorDatetime.now()
    status : TaskwarriorStatus = TaskwarriorStatus.PENDING
    id : int | None = None
    start : TaskwarriorDatetime | None = None
    end :  TaskwarriorDatetime | None = None
    due : TaskwarriorDatetime | None = None
    until : TaskwarriorDatetime | None = None 
    wait : TaskwarriorDatetime | None = None
    modified: TaskwarriorDatetime | None = None
    project : str | None = None
    tags : list[str] = field(default_factory=list)
    priority: TaskwarriorPriority | None = None
    urgency : int = 1
    
    # UDAs
    todoist : str | None = None
    timezone : str | None = None
    section : str | None = None

    @classmethod
    def from_taskwarrior(cls, json_data : Union[TaskwarriorDict,str]):
        '''Create TaskwarriorTask object from a JSON blob emitted by Taskwarrior
        
        Parameters
        ----------
        data : str, dict
            JSON str emitted by `task export`, or dict serialized from this str
        
        Returns
        -------
        out : TaskwarriorTask
        '''
        data : TaskwarriorDict
        if isinstance(json_data, dict):
            data = json_data 
        elif isinstance(json_data, str):
            data  = json.loads(json_data)
        out = cls(
            description= data['description'],
            uuid=uuid.UUID(data['uuid']),
            entry=TaskwarriorDatetime.from_taskwarrior(data['entry']),
            status=TaskwarriorStatus[data['status'].upper()],
        )
        # Optional includes
        for key in ['project', 'tags', 'urgency', 'timezone', 'todoist']:
            if key in data:
                setattr(out, key, data[key])
        # Cast ints
        for key in ['id']:
            if key in data:
                setattr(out, key, int(data[key]))
        # Cast datetimes
        for key in ['start', 'end', 'due', 'until', 'wait', 'modified']:
            if key in data:
                setattr(out, key, TaskwarriorDatetime.from_taskwarrior(data[key]))
        # Cast priority
        if 'priority' in data:
            out.priority = TaskwarriorPriority[data['priority']]
        return out

    def update(self, **kwargs):
        '''Update attributes on the task
        
        Parameters
        ----------
        kwargs : dict
            key-value pairs indicating attributes to update
        
        Returns
        -------
        None
        '''
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        return

    def to_dict(self, exclude_id=False) -> dict:
        '''Serialize task to a dict, suitable for presentation as JSON
        
        Note: Taskwarrior-specific types (e.g. TaskwarriorDatetime, etc.) will be serialized to str
        
        Parameters
        ----------
        exclude_id : bool, optional
            If True, will exclude the `id` attribute from the returned dict.
        '''
        out = {}
        if not exclude_id:
            out['id'] = self.id
        for attr in ['description', 'uuid', 'entry', 'status', 'start', 'end', 'due', 'modified', 'until', 'wait', 'project', 'priority']:
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
    
    def to_taskwarrior(self, exclude_id=False, **kwargs) -> str:
        '''Like `to_dict` but returns the value as a JSON string

        Use this method to convert objects into string representations suitable
        for consumption by Taskwarrior hooks.

        Parameters
        ----------
        exclude_id : bool, optional
            If True, will exclude the `id` attribute from the returned dict.
        **kwargs : optional
            Keyword arguments to pass to `json.dumps`
        '''
        return json.dumps(self.to_dict(exclude_id=exclude_id), **kwargs)
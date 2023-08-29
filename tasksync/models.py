from __future__ import annotations

import datetime
import json
import uuid
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Union, TypedDict

from todoist_api_python.models import Task as TodoistTask, Due as TodoistDue
from zoneinfo import ZoneInfo
import tzlocal

TODOIST_DUE_DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
TODOIST_DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'

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
    
    @classmethod
    def from_todoist(cls, value):
        '''Create from Todoist priority int'''
        # Todoist priorities differ by 1
        return cls(value - 1)
    
    def to_todoist(self):
        '''Convert to Todoist priority int'''
        return self.value + 1

class TaskwarriorDatetime(datetime.datetime):
    '''Class for storing Taskwarrior datetime values'''
    
    def __str__(self) -> str:
        # TODO: need this to be timezone aware?
        return self.strftime('%Y%m%dT%H%M%SZ')
    
    @classmethod
    def from_taskwarrior(cls, value):
        return cls.strptime(value, '%Y%m%dT%H%M%SZ').replace(tzinfo=ZoneInfo('UTC'))

    @classmethod 
    def from_todoist(cls, value):
        if isinstance(value, TodoistDue):
            if value.datetime is not None:
                return (cls
                        .strptime(value.datetime, TODOIST_DUE_DATETIME_FORMAT)
                        .replace(tzinfo=ZoneInfo('UTC'))
                )
            else:
                return (cls
                        .strptime(value.date, '%Y-%m-%d')
                        .replace(tzinfo=tzlocal.get_localzone().unwrap_shim()) # type: ignore
                        .astimezone(ZoneInfo('UTC'))
                )
        elif isinstance(value, str):
            return cls.strptime(value, TODOIST_DATETIME_FORMAT)

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
    todoist : Optional[int] = None
    timezone : str = tzlocal.get_localzone_name()

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
        for key in ['project', 'tags', 'urgency']:
            if key in data:
                setattr(out, key, data[key])
        # Cast ints
        for key in ['id', 'todoist']:
            if key in data:
                setattr(out, key, int(data[key]))
        # Cast datetimes
        for key in ['start', 'end', 'due', 'until', 'wait',' modified']:
            if key in data:
                setattr(out, key, TaskwarriorDatetime.from_taskwarrior(data[key]))
        # Cast priority
        if hasattr(data, 'priority'):
            out.priority = TaskwarriorPriority[data['priority']]
        return out

    @classmethod
    def from_todoist(cls, task : TodoistTask):
        '''Create TaskwarriorTask object from a Todoist API Task object
        
        Parameters
        ----------
        task: TodoistTask
            Task object returned by the `get_task` method from the Todoist API
        
        Returns
        -------
        out : TaskwarriorTask
        '''
        out = cls(
            uuid=uuid.uuid4(),
            description=task.content,
            entry=TaskwarriorDatetime.from_todoist(task.created_at),
            status=TaskwarriorStatus.COMPLETED if task.is_completed else TaskwarriorStatus.PENDING,
        )
        if task.due is not None:
            # TODO: Support datetimes
            task.due = TaskwarriorDatetime.from_todoist(task.due) # type: ignore
        if task.project_id != 'Inbox':
            out.project = task.project_id
        if len(task.labels) > 0:
            out.tags = task.labels
        if task.priority > 1:
            out.priority = TaskwarriorPriority.from_todoist(task.priority)
        out.todoist = int(task.id)
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
    
    def to_todoist_api_kwargs(self, sync=None) -> dict:
        '''Prepare dict of kwargs to pass to TodoistAPI methods

        Output from this method can be passed directly into `add_task`,
        `update_task`, etc.

        Returns
        -------
        kwargs : dict
            Keyword arguments for TodoistAPI methods
        '''
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
        if self.project and sync is not None:
            if project := sync.store.find('projects', name=self.project):
                kwargs['project_id'] = project['id']
            else:
                # Make the project
                temp_id = str(uuid.uuid4())
                sync.api.add_project(self.project, temp_id)
                res = sync.api.push()
                kwargs['project_id'] = res['temp_id_mapping'][temp_id]
                # Update projects in data store
                sync.api.pull(resource_types=['projects'])
                sync.store.load(resource_types=['projects'])
        return kwargs
    
def parse_todoist_due_datetime(due : TaskwarriorDatetime, timezone : str) -> tuple[str, str]:
    '''Helper function to convert TaskwarriorDatetime objects into key/value
    to include in TodoistAPI calls

    Parameters
    ----------
    due : TaskwarriorDatetime
        object specifying the due date of a task
    timezone : str
        IANA Zone ID for the timezone in which the task was created (e.g.
        America/New_York)
    
    Returns
    -------
    key : str
        keyword name to include in TodoistAPI calls
    value : str
        value for the corresponding keyword

    Notes
    -----
    Taskwarrior and Todoist store due dates slightly differently. Taskwarrior
    stores due dates - and all dates, for that matter - as a timezone-aware UTC
    timestamp. Todoist stores due dates as either a timezone-aware timestamp
    (defaults to UTC but can be changed) _or_ a date string. According to
    Todoist, the date string format makes it easier to accomodate
    timezone-dependent due dates (e.g. daily routines)
    
    We had to make an important assumption here based on these differences to
    avoid giving every task in Todoist an explicit time.
    
    - If a due date for a task in Taskwarrior is midnight on YYYY-mm-dd in the
      timezone in which the task was created, we map it to a `due_date` in
      Todoist of YYYY-mm-dd.
    - If a due date for a task in Taskwarrior is any other time on YYYY-mm-dd,
      we map it to a `due_datetime` 
    '''
    # Convert TaskwarriorDatetime to local timezone
    due_datetime = due.astimezone(ZoneInfo(timezone))
    if due_datetime.hour == 0 and due_datetime.minute == 0:
        return 'due_date', due.strftime('%Y-%m-%d')
    else:
        return 'due_datetime', due.strftime(TODOIST_DATETIME_FORMAT)
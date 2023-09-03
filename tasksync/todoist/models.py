from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TypedDict, Union

from models import TasksyncDatetime

class TodoistSyncDuration(TypedDict):
    amount : float
    unit : str

class TodoistSyncDue(TypedDict, total=False):
    date : str
    timezone : str | None
    string : str | None
    is_recurring : bool
    lang : str

class TodoistSyncTaskDict(TypedDict):
    added_at : str
    added_by_uid : str
    assigned_by_uid : str | None
    checked : bool
    child_order : int
    collapsed : bool
    completed_at : str | None
    content : str
    day_order : int
    description : str
    id : str
    is_deleted : bool
    labels : list[str]
    parent_id : str | None
    priority : int
    project_id : str
    responsible_uid : str | None
    section_id : str | None
    sync_id : str | None
    user_id : str

    due : TodoistSyncDue | None
    duration : TodoistSyncDuration | None


@dataclass
class TodoistSyncTask:
    added_at : str
    added_by_uid : str
    assigned_by_uid : str | None
    checked : bool
    child_order : int
    collapsed : bool
    completed_at : str | None
    content : str
    day_order : int
    description : str
    id : str
    is_deleted : bool
    labels : list[str]
    parent_id : str | None
    priority : int
    project_id : str
    responsible_uid : str | None
    section_id : str | None
    sync_id : str | None
    user_id : str

    due : TasksyncDatetime | None = None
    duration : TodoistSyncDuration | None = None

    @classmethod
    def from_todoist(cls, json_data : Union[TodoistSyncTaskDict, str]):
        data : TodoistSyncTaskDict
        if isinstance(json_data, str):
            data = json.loads(json_data)
        else:
            data = json_data

        out = cls(
            added_at=data['added_at'],
            added_by_uid=data['added_by_uid'],
            assigned_by_uid=data['assigned_by_uid'],
            checked=data['checked'],
            child_order=data['child_order'],
            collapsed=data['collapsed'],
            completed_at=data['completed_at'],
            content=data['content'],
            day_order=data['day_order'],
            description=data['description'],
            id=data['id'],
            is_deleted=data['is_deleted'],
            labels=data['labels'],
            parent_id=data['parent_id'],
            priority=data['priority'],
            project_id=data['project_id'],
            responsible_uid=data['responsible_uid'],
            section_id=data['section_id'],
            sync_id=data['sync_id'],
            user_id=data['user_id'],
            duration=data['duration'],
        )
        if data['due'] is not None:
            out.due = TasksyncDatetime.from_todoist(data['due'])
        return out

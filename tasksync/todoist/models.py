from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TypedDict, Union

from tasksync.models import TasksyncDatetime

class TodoistSyncDuration(TypedDict):
    amount : float
    unit : str

class TodoistSyncDue(TypedDict, total=False):
    date : str
    timezone : str | None
    string : str | None
    is_recurring : bool
    lang : str

class TodoistSyncTask(TypedDict):
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
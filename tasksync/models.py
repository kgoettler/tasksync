#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, TypedDict, Union, TYPE_CHECKING
from zoneinfo import ZoneInfo
import datetime
import json
import tzlocal

if TYPE_CHECKING:
    from taskwarrior.models import TaskwarriorDatetime
    from todoist.models import TodoistSyncDue

class TasksyncDateType(Enum):
    FLOATING_DATE = 0
    FLOATING_DATETIME = 1
    FIXED = 2

    def get_todoist_datetime_format(self) -> str:
        if self.value == 0:
            return '%Y-%m-%d'
        elif self.value == 1:
            return '%Y-%m-%dT%H:%M:%S'
        else:
            return '%Y-%m-%dT%H:%M:%S.%fZ'

class TasksyncDatetime(datetime.datetime):
    datetype : TasksyncDateType
    recurring : bool

    def __new__(cls,
                 *args,
                 datetype: TasksyncDateType = TasksyncDateType.FIXED,
                 recurring : bool = False,
                 **kwargs,
    ):
        self =  super().__new__(cls, *args, **kwargs)
        self.datetype = datetype
        self.recurring = recurring
        return self

    def __repr__(self):
        return '{}({})'.format(
            self.__class__.__qualname__,
            self.strftime(self.datetype.get_todoist_datetime_format()),
        )

    @classmethod 
    def from_taskwarrior(cls, value : TaskwarriorDatetime) -> TasksyncDatetime:
        new = cls(value)
        #new = cls.strptime(value, '%Y%m%dT%H%M%SZ').replace(tzinfo=ZoneInfo('UTC'))
        if new.hour == 0 and new.minute == 0:
            new.datetype = TasksyncDateType.FLOATING_DATE
        else:
            new.datetype = TasksyncDateType.FIXED
        return new
    
    @classmethod
    def from_todoist(cls, value : TodoistSyncDue) -> TasksyncDatetime:
        new = None
        for datetype in TasksyncDateType:
            try:
                new = cls.strptime(
                    value['date'],
                    datetype.get_todoist_datetime_format(),
                )
                if value['timezone']:
                    new = new.astimezone(ZoneInfo(value['timezone']))
                new.datetype = datetype
                break
            except Exception:
                pass
        if new is None:
            raise ValueError('Could not convert {} into TasksyncDatetime via from_todoist'.format(value['date']))
        return new
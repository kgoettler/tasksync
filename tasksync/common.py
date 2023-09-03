#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import datetime
import json
from typing import Optional, TypedDict, Union

from zoneinfo import ZoneInfo
import tzlocal

import tasksync.todoist as todoist

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
    def from_taskwarrior(cls, value) -> TasksyncDatetime:
        new = cls.strptime(value, '%Y%m%dT%H%M%SZ').replace(tzinfo=ZoneInfo('UTC'))
        if new.hour == 0 and new.minute == 0:
            new.datetype = TasksyncDateType.FLOATING_DATE
        else:
            new.datetype = TasksyncDateType.FIXED
        return new
    
    @classmethod
    def from_todoist(cls, value : todoist.TodoistSyncDue) -> TasksyncDatetime:
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

    def to_taskwarrior(self) -> str:
        if self.tzinfo is None:
            # Assume local timezone
            out = self.replace(tzinfo=tzlocal.get_localzone().unwrap_shim()) # type: ignore
        else:
            out = self
        return out.strftime(TASKWARRIOR_DATETIME_FORMAT)

    def to_todoist(self) -> todoist.TodoistSyncDue:
        out = todoist.TodoistSyncDue({
            'date': self.strftime(self.datetype.get_todoist_datetime_format()),
            'is_recurring': self.recurring,
        })
        if self.datetype == TasksyncDateType.FIXED:
            if tzinfo := self.tzinfo:
                timezone = self.tzinfo.key # type: ignore
            else:
                timezone = 'UTC'
            out['timezone'] = timezone
        return out
#!/usr/bin/env python3

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo
import datetime

if TYPE_CHECKING:
    from tasksync.todoist.models import TodoistSyncDue

TASKWARRIOR_DATETIME_FORMAT = "%Y%m%dT%H%M%SZ"


class TasksyncDateType(Enum):
    FLOATING_DATE = 0
    FLOATING_DATETIME = 1
    FIXED = 2

    def get_todoist_datetime_format(self) -> str:
        if self.value == 0:
            return "%Y-%m-%d"
        elif self.value == 1:
            return "%Y-%m-%dT%H:%M:%S"
        else:
            return "%Y-%m-%dT%H:%M:%SZ"


class TasksyncDatetime(datetime.datetime):
    datetype: TasksyncDateType
    recurring: bool

    def __new__(
        cls,
        *args,
        datetype: TasksyncDateType = TasksyncDateType.FIXED,
        recurring: bool = False,
        **kwargs,
    ):
        self = super().__new__(cls, *args, **kwargs)
        self.datetype = datetype
        self.recurring = recurring
        return self

    def __repr__(self):
        return "{}({})".format(
            self.__class__.__qualname__,
            self.strftime(self.datetype.get_todoist_datetime_format()),
        )

    @classmethod
    def from_taskwarrior(cls, value: str) -> TasksyncDatetime:
        new = cls.strptime(value, TASKWARRIOR_DATETIME_FORMAT).replace(
            tzinfo=ZoneInfo("UTC")
        )
        # new = cls.strptime(value, '%Y%m%dT%H%M%SZ').replace(tzinfo=ZoneInfo('UTC'))
        if new.hour == 0 and new.minute == 0:
            new.datetype = TasksyncDateType.FLOATING_DATE
        else:
            new.datetype = TasksyncDateType.FIXED
        return new

    @classmethod
    def from_todoist(cls, value: TodoistSyncDue) -> TasksyncDatetime | None:
        new = None
        for datetype in TasksyncDateType:
            try:
                new = cls.strptime(
                    value["date"],
                    datetype.get_todoist_datetime_format(),
                )
                if value["timezone"]:
                    new = new.astimezone(ZoneInfo(value["timezone"]))
                new.datetype = datetype
                break
            except Exception:
                pass
        if new is None and (date := value.get("date")):
            raise ValueError(
                "Could not convert {} into TasksyncDatetime via from_todoist".format(
                    date
                )
            )
        return new

    def to_taskwarrior(self) -> str:
        return self.strftime(TASKWARRIOR_DATETIME_FORMAT)

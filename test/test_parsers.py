#!/usr/bin/env python3

import pytest

from tasksync.taskwarrior import TaskwarriorDatetime, parse_todoist_due_datetime

sample_date = "20230828T040000Z"
sample_datetime = "20230828T130000Z"
timezone = 'America/New_York'

def test_taskwarrior_datetime_parse():
    value = TaskwarriorDatetime.from_taskwarrior(sample_date)
    assert value.strftime('%Y-%m-%d %H:%M:%S') == '2023-08-28 04:00:00'

def test_taskwarrior_convert_due_date():
    value = TaskwarriorDatetime.from_taskwarrior(sample_date)
    key, value = parse_todoist_due_datetime(value, timezone)
    assert key == 'due_date' and value == '2023-08-28'

def test_taskwarrior_convert_due_datetime():
    value = TaskwarriorDatetime.from_taskwarrior(sample_datetime)
    key, value = parse_todoist_due_datetime(value, timezone)
    assert key == 'due_datetime' and value == '2023-08-28T13:00:00.000000Z'
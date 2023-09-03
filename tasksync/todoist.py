#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from os.path import exists, join
import datetime
import json
import os
import uuid
from typing import Optional, TypedDict, Union
import requests

from zoneinfo import ZoneInfo
import tzlocal

import tasksync

TODOIST_SYNC_URL = 'https://api.todoist.com/sync/v9/sync'
CACHE_PATH = os.path.join(os.environ['HOME'], '.todoist')
if not exists(CACHE_PATH):
    os.makedirs(CACHE_PATH)

@dataclass
class SyncToken:
    '''Sync token returned by Todoist Sync API
    
    Basically a wrapper around a token (str) and a timestamp (int) but with a
    few goodies for convenience
    '''
    token : str
    timestamp : int = int(datetime.datetime.now().strftime('%s'))

    def __str__(self):
        return str(self.__dict__)

    def update(self, token, timestamp=None):
        self.token = token
        self.timestamp = timestamp if timestamp is not None else SyncToken.get_timestamp()
        return self

    @staticmethod
    def get_timestamp():
        return int(datetime.datetime.now().strftime('%s'))

@dataclass
class SyncTokenManager:
    '''Class to manage SyncTokens on a per-resource basis'''
    collaborator_states : SyncToken
    collaborators : SyncToken
    completed_info : SyncToken
    day_orders : SyncToken
    day_orders_timestamp : SyncToken
    due_exceptions : SyncToken
    filters : SyncToken
    full_sync : SyncToken
    incomplete_item_ids : SyncToken
    incomplete_project_ids : SyncToken
    items : SyncToken
    labels : SyncToken
    live_notifications : SyncToken
    live_notifications_last_read_id : SyncToken
    locations : SyncToken
    notes : SyncToken
    project_notes : SyncToken
    projects : SyncToken
    reminders : SyncToken
    sections : SyncToken
    stats : SyncToken
    tooltips : SyncToken
    user : SyncToken
    user_plan_limits : SyncToken
    user_settings : SyncToken
    view_options : SyncToken

    def __init__(self, basedir=None):
        if basedir is None:
            basedir = CACHE_PATH 
        self.tokens = {}
        self.file = join(basedir, 'sync_tokens.json')
        if exists(self.file):
            self.read()
            with open(self.file, 'r') as f:
                decoder = SyncTokenDecoder()
                self.tokens = decoder.decode(f.read())

    def __repr__(self):
        msg =  'SyncTokenManager'
        msg += 'File: {}'.format(self.file)
        for key, token in self.tokens.items():
            msg += '{:<15s}: {}'.format(key, token)
        return msg

    def get(self, resource_types=None) -> SyncToken:
        if resource_types is None:
            resource_types = list(self.__dataclass_fields__.keys())
        sync_token, timestamp = '*', int(datetime.datetime.max.strftime('%s'))
        for resource_type in resource_types:
            if token := self.tokens.get(resource_type, None):
                if token.timestamp < timestamp:
                    timestamp = token.timestamp
                    sync_token = token.token
        return SyncToken(
            token=sync_token,
            timestamp=timestamp if sync_token != '*' else int(datetime.datetime.min.strftime('%s')),
        )
    
    def set(self, sync_token, resource_types=None):
        if resource_types is None:
            resource_types = list(self.__dataclass_fields__.keys())
        # Get current timestamp
        timestamp = SyncToken.get_timestamp()
        for resource_type in resource_types:
            if token := self.tokens.get(resource_type, None):
                token.timestamp = timestamp
                token.token = sync_token
            else:
                self.tokens[resource_type] = SyncToken(sync_token, timestamp)
        return
    
    def read(self, file=None):
        if file is None:
            file = self.file
        with open(file, 'r') as f:
            decoder = SyncTokenDecoder()
            self.tokens = decoder.decode(f.read())
    
    def write(self, file=None):
        if file is None:
            file = self.file
        with open(file, 'w') as f:
            f.write(json.dumps(self.tokens, cls=SyncTokenEncoder))

class SyncTokenEncoder(json.JSONEncoder):
    '''JSON encoder for SyncToken objects'''
    def default(self, obj):
        return obj.__dict__    
    
class SyncTokenDecoder(json.JSONDecoder):
    '''JSON decoder for SyncToken objects'''
    def __init__(self):
        json.JSONDecoder.__init__(self, object_hook=self.dict_to_object)

    def dict_to_object(self, d):
        if 'token' in d and 'timestamp' in d:
            return SyncToken(token=d['token'], timestamp=d['timestamp'])
        return d

class TodoistSync:
    '''Class for interacting with the Todoist Sync API + local storage cache'''

    def __init__(self, api=None, store=None, basedir=None):
        self.api = api if api is not None else TodoistSyncAPI()
        if store is not None:
            self.store = store
        elif basedir is not None:
            self.store = TodoistSyncDataStore(basedir=basedir)
        else:
            raise ValueError('Must provide either \'store\' or \'basedir\' argument')
        return
    
class TodoistSyncDataStore:
    '''Local data store for managing interactions with the Todoist Sync API'''

    def __init__(self, basedir=None):
        self.basedir = CACHE_PATH if basedir is None else basedir
        self.resource_types = ['items', 'labels', 'projects', 'sections']
        self.items = []
        self.labels = []
        self.projects = []
        self.sections = []
        self.load()

    def save(self, resource_types=[]):
        if len(resource_types) == 0:
            resource_types = self.resource_types
        for key in resource_types:
            update_local_data(getattr(self, key), join(self.basedir, '{}.json'.format(key)))

    def load(self, resource_types=[]):
        if len(resource_types) == 0:
            resource_types = self.resource_types
        for key in resource_types:
            datafile = join(self.basedir, '{}.json'.format(key))
            if exists(datafile):
                with open(datafile, 'r') as f:
                    setattr(self, key, json.load(f))
            else:
                setattr(self, key, {})

    # TODO: find out why this is considerably faster than the ones below...
    # top:     841 ns ± 4.94 ns
    # middle: 2.11 µs ± 3.76 ns
    # bottom: 1.11 µs ± 1.96 ns
    def find(self, key, **kwargs):
        if key not in self.resource_types:
            raise ValueError('\'{}\' is not a valid data type'.format(key))
        for element in getattr(self, key):
            match = True
            for k, v in kwargs.items():
                if element[k] != v:
                    match = False
                    break
            if match:
                return element
        return
    
    #def find(self, key, **kwargs):
    #    if key not in self.resource_types:
    #        raise ValueError('\'{}\' is not a valid data type'.format(key))
    #    def filter_func(element, kwargs):
    #        return all([element.get(x, None) == y for x,y in kwargs.items()])
    #    return next((x for x in getattr(self, key) if filter_func(x, kwargs)), None)

    #def find(self, key, **kwargs):
    #    if key not in self.resource_types:
    #        raise ValueError('\'{}\' is not a valid data type'.format(key))
    #    for element in getattr(self, key):
    #        if match := filter_func(element, kwargs):
    #            return match
    #    return

def filter_func(element, kwargs):
    for k, v in kwargs.items():
        if element.get(k, None) != v:
            return None
    return element

class TodoistSyncAPI:
    '''Main class for interacting with Todoist Sync API'''

    def __init__(self):
        self.commands = []
        self.token_manager = SyncTokenManager()
        return

    def load_data(self):
        data_file = join(CACHE_PATH, 'data.json')
        if not exists(data_file):
            self.pull()
        with open(data_file, 'r') as f:
            data = json.load(f)
        return data

    def pull(self, sync_token=None, resource_types=None):
        if sync_token is None:
            sync_token_obj = self.token_manager.get(resource_types)
            sync_token = sync_token_obj.token

        if resource_types is None:
            resource_types = []
        res = requests.post(
            TODOIST_SYNC_URL,
            headers={
                'Authorization': 'Bearer {}'.format(os.environ['TODOIST_API_KEY']),
            },
            data={
                'sync_token': sync_token, 
                'resource_types': '["all"]' if len(resource_types) == 0 else str(resource_types).replace('\'', '\"'),
            }
        )
        if res.status_code != 200:
            raise RuntimeError('sync error ({})'.format(res.status_code))
            
        # Serialize & write 
        data = json.loads(res.text)
        write_local_data(data, CACHE_PATH, overwrite=sync_token == '*')
        # Update tokens
        self.token_manager.set(
            data['sync_token'],
            list(data.keys()) if len(resource_types) == 0 else resource_types
        )
        self.token_manager.write()
        return data

    def push(self):
        if len(self.commands) == 0:
            return {}
        res = requests.post(
            TODOIST_SYNC_URL,
            headers={
                'Authorization': 'Bearer {}'.format(os.environ['TODOIST_API_KEY']),
            },
            json={
                'commands': self.commands,
            }
        )
        if res.status_code != 200:
            raise RuntimeError('sync error ({})'.format(res.status_code))
        
        # Serialize
        data = json.loads(res.text)
        return data

    def clear(self):
        self.commands = []
        return

def write_local_data(data, outdir, overwrite=False):
    data_file = join(outdir, 'data.json')
    if overwrite:
        with open(data_file, 'w') as f:
            json.dump(data, f)
    keys = ['items', 'labels', 'projects', 'sections']
    for key in keys:
        if key in data:
            update_local_data(data[key], join(outdir, '{}.json'.format(key)))
    return

def update_local_data(data, data_file):
    # Read
    if exists(data_file):
        with open(data_file, 'r') as f:
            old_data = sorted(json.load(f), key=lambda x: x['id'])
        # Update
        for elem in data:
            # Update (if already exists) or append
            if old_elem := next((x for x in old_data if x["id"] == elem['id']), None):
                old_elem.update(elem)
            else:
                old_data.append(elem)
    else:
        old_data = data
    # Write
    with open(data_file, 'w') as f:
        json.dump(old_data, f)
    return old_data

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

    due : tasksync.TasksyncDatetime | None = None
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
            out.due = tasksync.TasksyncDatetime.from_todoist(data['due'])
        return out
    
    def to_taskwarrior(self) -> tasksync.TaskwarriorTask:
        return
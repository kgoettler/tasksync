#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass
from os.path import exists, join
import datetime
import json
import os
import uuid
from typing import Optional, TypedDict

import requests

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

class SyncTokenDict(TypedDict):
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

class SyncTokenManager:
    '''Class to manage SyncTokens on a per-resource basis'''
    basedir : str
    file : str
    tokens : SyncTokenDict

    def __init__(self, basedir=None):
        if basedir is None:
            basedir = CACHE_PATH 
        self.basedir = basedir
        self.file = join(basedir, 'sync_tokens.json')
        if exists(self.file):
            self.load()
        else:
            timestamp = SyncToken.get_timestamp()
            self.tokens = SyncTokenDict(**{
                key:SyncToken('*', timestamp) for key in SyncTokenDict.__required_keys__
            })

    def __repr__(self):
        msg =  'SyncTokenManager'
        msg += '\nFile: {}'.format(self.file)
        for key, token in self.tokens.items(): # type: ignore
            msg += '\n{:<15s}: {}'.format(key, token)
        return msg
    
    def get(self, resource_types=None) -> SyncToken:
        if resource_types is None:
            resource_types = list(self.tokens.keys())
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
            resource_types = list(self.tokens.keys())
        # Get current timestamp
        timestamp = SyncToken.get_timestamp()
        for resource_type in resource_types:
            if token := self.tokens.get(resource_type, None):
                token.timestamp = timestamp
                token.token = sync_token
            else:
                self.tokens[resource_type] = SyncToken(sync_token, timestamp)
        return
    
    def load(self, file=None):
        if file is None:
            file = self.file
        with open(file, 'r') as f:
            decoder = SyncTokenDecoder()
            self.tokens = decoder.decode(f.read())
    
    def save(self, file=None):
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
        if store is not None and basedir is not None:
            raise ValueError('\'store\' and \'basedir\' arguments are mutually exclusive')
        elif store is not None:
            self.store = store
        elif basedir is not None:
            self.store = TodoistSyncDataStore(basedir=basedir)
        else:
            raise ValueError('Must provide either \'store\' or \'basedir\' argument')
        return

    def pull(self, sync_token=None, resource_types=None):
        if sync_token is None:
            sync_token = self.store.tokens.get(resource_types=resource_types)
        # Pull data
        updated_data = self.api.pull(
            sync_token=sync_token,
            resource_types=resource_types,
        )
        # Update the data store
        self.store.update(
            updated_data,
            resource_types=resource_types,
        )
        return updated_data
    

    def push(self, commands=None):
        # TODO: Perform pull here to update store?
        return self.api.push(commands=commands)
    
class TodoistSyncDataStore:
    '''Local data store for managing interactions with the Todoist Sync API'''
    items : list
    labels : list
    projects : list
    sections : list
    tokens : SyncTokenManager

    def __init__(self, basedir=None):
        self.basedir = CACHE_PATH if basedir is None else basedir
        self.tokens = SyncTokenManager(basedir=self.basedir)
        self.resource_types = ('items', 'labels', 'projects', 'sections')
        self.load()

    def save(self, resource_types=[]):
        if len(resource_types) == 0:
            resource_types = self.resource_types
        for resource_type in resource_types:
            with open(join(self.basedir, '{}.json'.format(resource_type)), 'w') as f:
                json.dump(getattr(self, resource_type), f)
        return

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

    def update(self, data, resource_types=None):
        if resource_types is None:
            resource_types = self.resource_types
        self.tokens.set(data['sync_token'], resource_types=resource_types)
        self.tokens.save()

        # Update data
        for resource_type in resource_types:
            for elem in data.get(resource_type, []):
                # Find this in the current dataset
                # Update (if already exists) or append
                if existing_elem := next((x for x in getattr(self, resource_type) if x['id'] == elem['id']), None):
                    existing_elem.update(elem)
                else:
                    getattr(self, resource_type).append(elem)
        self.save(resource_types=resource_types)
        return

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
    
    def find_all(self, key, **kwargs):
        if key not in self.resource_types:
            raise ValueError('\'{}\' is not a valid data type'.format(key))
        matches = []
        for element in getattr(self, key):
            match = True
            for k, v in kwargs.items():
                if element[k] != v:
                    match = False
                    break
            if match:
                matches.append(element)
        return matches
    
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

#def filter_func(element, kwargs):
#    for k, v in kwargs.items():
#        if element.get(k, None) != v:
#            return None
#    return element

class TodoistSyncAPI:
    '''Main class for interacting with Todoist Sync API'''
    commands : list

    def __init__(self):
        self.commands = []
        return

    def pull(self, sync_token=None, resource_types=None):
        # Perform full sync if no token provided
        if sync_token is None:
            sync_token = '*'

        # Execute POST request
        res = requests.post(
            TODOIST_SYNC_URL,
            headers={
                'Authorization': 'Bearer {}'.format(os.environ['TODOIST_API_KEY']),
            },
            data={
                'sync_token': sync_token, 
                'resource_types': '["all"]' if resource_types is None else str(resource_types).replace('\'', '\"'),
            }
        )
        if res.status_code != 200:
            raise RuntimeError('sync error ({})'.format(res.status_code))
        
        # Serialize response and write to local file
        data = json.loads(res.text)
        return data

    def push(self, commands=None):
        if commands is None:
            commands = self.commands
            clear_commands = True
        else:
            clear_commands = False

        # Return empty dict if no commands to execute
        if len(commands) == 0:
            return {}
        
        # POST
        res = requests.post(
            TODOIST_SYNC_URL,
            headers={
                'Authorization': 'Bearer {}'.format(os.environ['TODOIST_API_KEY']),
            },
            json={
                'commands': commands,
            }
        )

        # Raise exception if sync did not complete properly
        if res.status_code != 200:
            raise RuntimeError('sync error ({})'.format(res.status_code))
        elif clear_commands:
            self.clear_commands()
        
        # Serialize response + return
        data = json.loads(res.text)
        return data
    
    def clear_commands(self):
        self.commands.clear()
        return
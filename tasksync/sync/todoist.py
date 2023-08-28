#!/usr/bin/env python3

from dataclasses import dataclass
from os.path import basename, dirname, exists, join
import datetime
import json
import os
import uuid
from typing import TypedDict

import requests

TODOIST_SYNC_URL = 'https://api.todoist.com/sync/v9/sync'
CACHE_PATH = os.path.join(os.environ['HOME'], '.todoist')
if not exists(CACHE_PATH):
    os.makedirs(CACHE_PATH)

class DefaultEncoder(json.JSONEncoder):
    def default(self, obj):
        return obj.__dict__    
    
class SyncTokenDecoder(json.JSONDecoder):
    def __init__(self):
        json.JSONDecoder.__init__(self, object_hook=self.dict_to_object)

    def dict_to_object(self, d):
        if 'token' in d and 'timestamp' in d:
            return SyncToken(token=d['token'], timestamp=d['timestamp'])
        return d

@dataclass
class SyncToken:
    token : str
    timestamp : int = int(datetime.datetime.now().strftime('%s'))

    def __str__(self):
        return str(self.__dict__)

    def update(self, token, timestamp=None):
        self.token = token
        self.timestamp = timestamp if timestamp is not None else SyncToken.get_timestamp()
        return self

    def to_json(self):
        return json.dumps(self.__dict__)
    
    @staticmethod
    def get_timestamp():
        return int(datetime.datetime.now().strftime('%s'))

@dataclass
class SyncTokenManager:
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

    def __init__(self):
        self.tokens = {}
        self.file = join(CACHE_PATH, 'sync_tokens.json')
        if exists(self.file):
            with open(self.file, 'r') as f:
                decoder = SyncTokenDecoder()
                self.tokens = decoder.decode(f.read())

    def __repr__(self):
        msg =  'SyncTokenManager'
        msg += 'File: {}'.format(self.file)
        for key, token in self.tokens.items():
            msg += '{:<15s}: {}'.format(key, token)
        print(msg)

    def decode(self):
        return self.__dict__
        
    def get(self, resource_types=[]):
        sync_token, timestamp = '*', int(datetime.datetime.max.strftime('%s'))
        for resource_type in resource_types:
            if token := self.tokens.get(resource_type, None):
                if token.timestamp < timestamp:
                    timestamp = token.timestamp
                    sync_token = token.token
        return sync_token
    
    def set(self, sync_token, resource_types):
        timestamp = SyncToken.get_timestamp()
        for resource_type in resource_types:
            if token := self.tokens.get(resource_type, None):
                token.timestamp = timestamp
                token.token = sync_token
            else:
                self.tokens[resource_type] = SyncToken(sync_token, timestamp)
        return
    
    def write(self, file=None):
        if file is None:
            file = self.file
        with open(file, 'w') as f:
            f.write(json.dumps(self.tokens, cls=DefaultEncoder))

class TodoistSync:

    def __init__(self):
        self.commands = []
        self.token_manager = SyncTokenManager()
        return

    def load_data(self):
        data_file = join(CACHE_PATH, 'data.json')
        if not exists(data_file):
            self.sync()
        with open(data_file, 'r') as f:
            data = json.load(f)
        return data

    def pull(self, sync_token=None, resource_types=[]):
        if sync_token is None:
            sync_token = self.token_manager.get(resource_types)
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


    def add_item(self, content: str, temp_id: str, **kwargs):
        endpoint = 'item_add'
        command = {
            "type": endpoint,
            "uuid": str(uuid.uuid4()),
            "temp_id": temp_id,
            "args": {
                "content": content
            }
        }
        self.__add_kwargs_to_command(command, **kwargs)
        self.commands.append(command)
        return

    def complete_item(self, id: str, temp_id: str, date_completed: str = None):
        command = {
            'type': 'item_complete',
            'uuid': str(uuid.uuid4()),
            'temp_id': temp_id,
            'args': {
                'id': id,
            }
        }
        if date_completed is not None:
            command['args']['date_completed'] = date_completed
        self.commands.append(command)
        return

    def delete_item(self, id: str, temp_id: str):
        command = {
            'type': 'item_delete',
            'uuid': str(uuid.uuid4()),
            'temp_id': temp_id,
            'args': {
                'id': id,
            }
        }
        self.commands.append(command)
        return

    def update_item(self, id: str, temp_id: str, **kwargs):
        endpoint = 'item_update'
        command = {
            'type': endpoint,
            'uuid': str(uuid.uuid4()),
            'temp_id': temp_id,
            'args': {
                'id': id,
            }
        }
        self.__add_kwargs_to_command(command, **kwargs)
        self.commands.append(command)
        return

    def move_item(self, id: str, temp_id: str, **kwargs):
        endpoint = 'item_move'
        command = {
            'type': endpoint,
            'uuid': str(uuid.uuid4()),
            'temp_id': temp_id,
            'args': {
                'id': id
            }
        }
        self.__add_kwargs_to_command(command, **kwargs)
        self.commands.append(command)
        return

    def add_section(self, name: str, temp_id: str, project_id: str, **kwargs):
        endpoint = 'section_add'
        command = {
            'type': endpoint,
            'uuid': str(uuid.uuid4()),
            'temp_id': temp_id,
            'args': {
                'name': name,
                'project_id': project_id,
            }
        }
        self.__add_kwargs_to_command(command, **kwargs)
        self.commands.append(command)
        return

    def __add_kwargs_to_command(self, command, **kwargs):
        for key, value in kwargs.items():
            command['args'][key] = value

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
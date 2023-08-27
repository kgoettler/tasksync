#!/usr/bin/env python3

from dataclasses import dataclass
from os.path import basename, dirname, exists, join
import json
import os
import uuid
from typing import TypedDict

import requests

TODOIST_SYNC_URL = 'https://api.todoist.com/sync/v9/sync'
CACHE_PATH = os.path.join(os.environ['HOME'], '.todoist')
if not exists(CACHE_PATH):
    os.makedirs(CACHE_PATH)

ALLOWED_KWARGS = {
    'item_add': {
        'temp_id',
        'description',
        'project_id',
        'due',
        'priority',
        'parent_id',
        'child_order',
        'section_id',
        'day_order',
        'collapsed',
        'labels',
        'assigned_by_uid',
        'responsible_uid',
        'auto_reminder',
        'auto_parse_labels',
    },
    'item_update': {
        'content',
        'description',
        'due',
        'priority',
        'collapsed',
        'labels',
        'assigned_by_uid',
        'responsible_uid',
        'day_order',
    },
    'item_move': {
        'parent_id',
        'section_id',
        'project_id',
    },
    'section_add': {
        'section_order'
    }
}

class TodoistSync:

    def __init__(self):
        self.commands = []
        return

    def load_data(self):
        data_file = join(CACHE_PATH, 'data.json')
        if not exists(data_file):
            self.sync()
        with open(data_file, 'r') as f:
            data = json.load(f)
        return data

    def sync(self, sync_token=None):

        if sync_token is None:
            # Check for token file
            token_file = join(CACHE_PATH, 'sync_token')
            if exists(token_file):
                with open(token_file, 'r') as f:
                    sync_token = f.read()
            else:
                sync_token = '*'
        headers = {
            'Authorization': 'Bearer {}'.format(os.environ['TODOIST_API_KEY']),
        }
        data = {
            'sync_token': sync_token, 
            'resource_types': '["all"]',
        }
        res = requests.post(TODOIST_SYNC_URL, headers=headers, data=data)

        if res.status_code != 200:
            raise RuntimeError('sync error ({})'.format(res.status_code))
            
        # Serialize response to JSON
        # Write to file
        data = json.loads(res.text)
        write_local_data(
            data,
            CACHE_PATH,
            sync_token=sync_token,
        )
        return data

    def run(self):
        if len(self.commands) == 0:
            return {}
        url = 'https://api.todoist.com/sync/v9/sync'
        headers = {
            'Authorization': 'Bearer {}'.format(os.environ['TODOIST_API_KEY']),
        }
        data = {
            'commands': self.commands,
        }
        res = requests.post(url, headers=headers, json=data)

        if res.status_code != 200:
            raise RuntimeError('sync error ({})'.format(res.status_code))
        
        # Serialize response to JSON
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
            if key not in ALLOWED_KWARGS[command['type']]:
                raise KeyError('{} is not a valid argument to {} endpoint'.format(key, command['type']))
            command['args'][key] = value

    def clear(self):
        self.commands = []
        return

def write_local_data(data, outdir, sync_token='*'):
    data_file = join(outdir, 'data.json')
    token_file = join(outdir, 'sync_token')
    if sync_token != '*':
        update_local_data(
            data,
            data_file,
        )
    else:
        with open(data_file, 'w') as f:
            json.dump(data, f)
    with open(token_file, 'w') as f:
        f.write(data['sync_token'])
    return

def update_local_data(data, data_file):
    with open(data_file, 'r') as f:
        old_data = json.load(f)

    # Handle just items for now...
    existing_ids = set([item['id'] for item in old_data['items']])
    updated_ids = set([item['id'] for item in data['items']])
    
    items = data['items'].copy()
    ids = set([item['id'] for item in items])
    for item in old_data['items']:
        if item['id'] in ids:
            continue
        items.append(item)
    old_data['items'] = items
    
    # Write back to file
    with open(data_file, 'w') as f:
        json.dump(old_data, f)
    return


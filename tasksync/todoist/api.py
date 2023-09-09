#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass
from os.path import exists, join
import datetime
import inspect
import json
import os
import uuid
from typing import Optional, TypedDict, Callable

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

import functools
def add_optional_kwargs(func : Callable):
    '''Log the date and time of a function'''

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        fsig = inspect.signature(func)
        accepted_args = inspect.signature(func).parameters
        data = func(*args, **{x:y for x,y in kwargs.items() if fsig.parameters[x].default is inspect._empty})
        for key, value in kwargs.items():
            if key not in accepted_args:
                raise TypeError('{} got an unexpected keyword argument \'{}\''.format(func.__qualname__, key))
            data['args'][key] = value
        return data
    return wrapper

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
    

    @staticmethod
    @add_optional_kwargs
    def add_item(
        content : str,
        temp_id : str,
        description : str | None = None,
        project_id : str | None = None,
        due : dict | None = None,
        priority : int | None = None,
        parent_id : str | None = None,
        child_order : int | None = None,
        section_id : str | None = None,
        day_order : int | None = None,
        collapsed : bool | None = None,
        labels : list[str] | None = None,
        assigned_by_uid : str | None = None,
        responsible_uid : str | None = None,
        auto_reminder : bool | None = None,
        auto_parse_labels : bool | None = None,
        duration : dict | None = None,
    ) -> dict:
        """Add a new item

        Parameters
        ----------
        content : str
            Text of the task
        temp_id : str
            Temporary uuid to refer to the task in successive API calls
        description : str | None, optional
            Description of the task
        project_id : str | None, optional
            ID of the project in which to place the task
        due : dict | None, optional
            Due date of the task
        priority : int | None, optional
            Priority of the task (1 = lowest, 4 = highest)
        parent_id : str | None, optional
            ID of parent task
        child_order : int | None, optional
            Order of the task in the parent
        section_id : str | None, optional
            ID of the section in which to place the task
        day_order : int | None, optional
            Order of the task inside the "Today" or "Next 7 days" views
        collapsed : bool | None, optional
            Whether hte task's subtasks are collapsed
        labels : list[str] | None, optional
            Task labels
        assigned_by_uid : str | None, optional
            ID of the user who assigns the task
        responsible_uid : str | None, optional
            ID of the user who is responsible for the task
        auto_reminder : bool | None, optional
            Whether to add a default reminder if due datetime is set
        auto_parse_labels : bool | None, optional
            Whether to autoparse labels from the task content
        duration : dict | None, optional
            Duration of the task 

        Returns
        -------
        data : dict
            API payload
        """
        data = {
            'type': 'item_add',
            'uuid': str(uuid.uuid4()),
            'temp_id': temp_id,
            'args': {
                'content': content,
            }
        }
        return data
    
    @staticmethod
    @add_optional_kwargs
    def modify_item(
        id_ : str,
        content : str | None = None,
        description : str | None = None,
        due : dict | None = None,
        priority : int | None = None,
        collapsed : bool | None = None,
        labels : list[str] | None = None,
        assigned_by_uid : str | None = None,
        day_order : int | None = None,
        duration : dict | None = None,
    ) -> dict:
        """Modify an item

        Parameters
        ----------
        id_ : str
            ID of the task
        content : str | None, optional
            Updated text of the task
        description : str | None, optional
            Update description of the task
        due : dict | None, optional
            Due date of the task; set to None to remove any existing due date
        priority : int | None, optional
            Priority; set to None to remove any priority
        collapsed : bool | None, optional
            Whether the task's subtasks are collapsed
        labels : list[str] | None, optional
            Update labels for task
        assigned_by_uid : str | None, optional
            Updated ID of the user who assigned the task
            _description_, by default None
        day_order : int | None, optional
            Updated order of the task inside the "Today" or "Next 7 days" views
        duration : dict | None, optional
            Updated duration of the task

        Returns
        -------
        data : dict
            API payload
        """
        data = {
            'type': 'item_update',
            'uuid': str(uuid.uuid4()),
            'args': {
                'id': id_,
            }
        }
        return data
    
    @staticmethod
    @add_optional_kwargs
    def move_item(
        id_ : str,
        parent_id : str | None = None,
        section_id : str | None = None,
        project_id : str | None = None,
    ) -> dict:
        """Move an item

        Parameters
        ----------
        id_ : str
            ID of the task
        parent_id : str | None, optional
            ID of the parent task to which the current task should be moved
        section_id : str | None, optional
            ID of the section to which the current task should be moved
        project_id : str | None, optional
            ID of the project to which the current task should be moved

        Returns
        -------
        data : dict
            API payload

        Notes
        -----
        To move an item from a section to no section, just use the `project_id`
        parameter with the project it currently belongs to as a value.
        """
        data = {
            'type': 'item_move',
            'uuid': str(uuid.uuid4()),
            'args': {
                'id': id_,
            }
        }
        return data
    

    @staticmethod
    @add_optional_kwargs
    def delete_item(
        id_ : str,
    ) -> dict:
        """Delete a task

        Parameters
        ----------
        id_ : str
            ID of the task to delete

        Returns
        -------
        data : dict
            API payload
        """
        data = {
            'type': 'item_delete',
            'uuid': str(uuid.uuid4()),
            'args': {
                'id': id_,
            }
        }
        return data
    
    @staticmethod
    @add_optional_kwargs
    def complete_item(
        id_ : str,
        date_completed : str | None = None
    ) -> dict:
        """Complete a task

        Parameters
        ----------
        id_ : str
            ID of the task to complete
        date_completed : str | None, optional
            RFC3339-formatted datetime at which the task was completed. If None,
            server will set the value to the current datetime.

        Returns
        -------
        data : dict
            API payload
        """
        data = {
            'type': 'item_complete',
            'uuid': str(uuid.uuid4()),
            'args': {
                'id': id_,
            }
        }
        return data

    @staticmethod
    def uncomplete_item(
        id_ : str,
    ) -> dict:
        """Uncomplete a task

        Parameters
        ----------
        id_ : str
            ID of the task to complete

        Returns
        -------
        data : dict
            API payload
        """
        data = {
            'type': 'item_uncomplete',
            'uuid': str(uuid.uuid4()),
            'args': {
                'id': id_,
            }
        }
        return data

    @staticmethod 
    @add_optional_kwargs
    def create_project(
        name : str,
        temp_id : str,
        color : str | None = None,
        parent_id : str | None = None,
        child_order : int | None = None,
        is_favorite : bool | None = None,
        view_style : str | None = None
    ) -> dict:
        """Create a new project

        Parameters
        ----------
        name : str
            Name of the project
        temp_id : str | None, optional
            Temporary uuid to refer to the task in successive API calls
        color : str | None, optional
            Color of the project icon
        parent_id : str | None, optional
            ID of the parent project
        child_order : int | None, optional
            Order of the project
        is_favorite : bool | None, optional
            Whether the project is a favorite
        view_style : str | None, optional
            String value (list | board) indicating the way the project is
            displayed within Todoist clients

        Returns
        -------
        data : dict 
            project_add payload
        """
        data = {
            'type': 'project_add',
            'uuid': str(uuid.uuid4()),
            'temp_id': temp_id,
            'args': {
                'name': name,
            }
        }
        return data

    @staticmethod
    @add_optional_kwargs
    def create_section(
        name : str,
        temp_id : str,
        project_id : str,
        section_order : int | None = None
    ) -> dict:
        """Create a new section

        Parameters
        ----------
        name : str
            Section name
        temp_id : str
            Temporary UUID; used to refer to the section in subsequent calls
        project_id : str
            Project ID in which the section will be located
        section_order : int | None, optional
            Order in which the section should appear in the project

        Returns
        -------
        data : dict
            API payload
        """
        data = {
            'type': 'section_add',
            'uuid': str(uuid.uuid4()),
            'temp_id': temp_id,
            'args': {
                'name': name,
            }
        }
        return data
    

if __name__ == '__main__':

    api = TodoistSyncAPI()
    print(TodoistSyncAPI.add_item(
        'New Item',
        str(uuid.uuid4()),
        project_id='1123',
    ))
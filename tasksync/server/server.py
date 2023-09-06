from __future__ import annotations

import os
import json
import logging
import pickle
import socket
import sys

from tasksync.server import (
    SOCKET_PATH,
    SERVER_TIMEOUT,
    CONNECTION_TIMEOUT,
    MAX_BUFFER_SIZE,
    send_data,
    receive_data,
)
from tasksync.taskwarrior import TaskwarriorTask

from tasksync.todoist.provider import TodoistProvider

class TasksyncServer:


    def __init__(self, 
                 socket_path : str = SOCKET_PATH,
                 server_timeout: int = SERVER_TIMEOUT,
                 loglevel : int = logging.DEBUG,
    ):
        self.socket_path = socket_path
        self.server_timeout = server_timeout
        self.provider = TodoistProvider()

        # Setup logger
        self.logger = logging.getLogger('tasksync')
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(loglevel)
        formatter = logging.Formatter('{asctime} | {levelname:<8s} | {name} | {message}', style='{')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(loglevel)
        self.logger.info('Starting Tasksync server')

        # Setup socket
        # remove the socket file if it already exists
        self.logger.debug('Creating socket at {}'.format(self.socket_path))
        try:
            os.unlink(self.socket_path)
        except OSError:
            if os.path.exists(self.socket_path):
                raise
        self.server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server.settimeout(self.server_timeout)
        self.server.bind(self.socket_path)

        # Allocate list for storing todoist commands
        self.commands = []

    def start(self):
        # Listen for incoming connections
        self.server.listen(1)
        self.logger.debug('Server is listening for incoming connections...')
        while True:
            try:
                self.accept()
            except socket.timeout as err:
                self.sync()
            except TasksyncTermination:
                self.logger.info('Tasksync shutting down (per request)')
                self.stop()
            except Exception as err:
                self.logger.error(self._get_error_message(err))
                self.stop(exit_code=100)
        return
    
    def stop(self, sync_updates=True, exit_code=0):
        # Sync updates (if indicated)
        if sync_updates and self.provider.updated:
            self.logger.debug('Syncing unsaved changes')
            self.sync()
            self.logger.debug('Complete')

        # Clean up socket
        os.unlink(self.socket_path)

        # Exit clean
        sys.exit(exit_code)

    def sync(self):
        if self.provider.updated:
            self.provider.push()
    
    def accept(self):
        connection, client_address = self.server.accept()
        self.logger.debug('Connection received')
        connection.settimeout(CONNECTION_TIMEOUT)
        try:
            data = receive_data(connection)
            feedback = self._process(data)
            send_data(connection, feedback)
        except socket.timeout:
            raise TasksyncTimeoutError()
        except Exception as err:
            send_data(connection, self._get_error_message(err))
            connection.close()
            raise err
        else:
            connection.close()

    def _get_error_message(self, err) -> str:
        return '{} raised: {}'.format(type(err).__name__, err)

    def _process(self, data: dict):
        # Ensure data received has a method attr
        if 'method' not in data:
            raise TasksyncBadRequestError('No method specified')

        # Process data
        if _processor := self._processor_map.get(data['method']):
            return _processor(self, data)
        else:
            raise TasksyncUnknownMethodError(
                'No processor defined for method \'{}\''.format(data['method'])
            )
        
    def _process_on_add(self, data : dict) -> str:
        task = TaskwarriorTask.from_taskwarrior(data['args'][0])
        task_str_out, feedback = self.provider.on_add(task)
        return feedback
    
    def _process_on_modify(self, data : dict) -> str:
        task_old, task_new = [TaskwarriorTask.from_taskwarrior(x) for x in data['args']]
        task_str_out, feedback = self.provider.on_modify(task_old, task_new)
        return feedback
    
    def _process_status(self, data : dict) -> str:
        return str(os.getpid())
    
    def _process_stop(self, data : dict) -> str:
        raise TasksyncTermination('Tasksync shutting down...')
    
    _processor_map = {
        'on-add': _process_on_add,
        'on-modify': _process_on_modify,
        'status': _process_status,
        'stop': _process_stop,
    }


class TasksyncServerError(Exception):
    pass

class TasksyncBadRequestError(Exception):
    pass

class TasksyncUnknownMethodError(Exception):
    pass

class TasksyncTermination(Exception):
    pass

class TasksyncTimeoutError(Exception):
    pass

if __name__ == '__main__':
    server = TasksyncServer()
    server.start()
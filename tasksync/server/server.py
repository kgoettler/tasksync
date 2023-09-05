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
        self.logger.debug('Starting Tasksync server')
        self.logger.setLevel(loglevel)

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
                self.receive()
            except socket.error as err:
                if err.args[0] == 'timed out':
                    self.logger.debug('Server timeout reached')
                    self.sync()
                else:
                    raise err
            except KeyboardInterrupt:
                self.stop()
                break
        return
    
    def stop(self):
        os.unlink(self.socket_path)
        return

    def sync(self):
        self.provider.push()
        return
    
    def receive(self):
        connection, client_address = self.server.accept()
        self.logger.debug('Connection received')
        connection.settimeout(CONNECTION_TIMEOUT)
        try:
            self._receive_data(connection)
        except socket.error as err:
            connection.close()
            raise err
        return
    
    def _receive_data(self, connection : socket.socket):
        # Receive data from client
        data = receive_data(connection)

        # Send to provider
        if data['type'] == 'on-add':
            task = TaskwarriorTask.from_taskwarrior(data['args'][0])
            task_str_out, feedback = self.provider.on_add(task)
        elif data['type'] == 'on-modify':
            task_old, task_new = [TaskwarriorTask.from_taskwarrior(x) for x in data['args']]
            task_str_out, feedback = self.provider.on_modify(task_old, task_new)
        else:
            raise TasksyncServerError('Unrecognized payload type: \'{}\''.format(data['type']))

        # Send feedback to client
        send_data(connection, feedback)
        return

class TasksyncServerError(Exception):
    pass

if __name__ == '__main__':
    server = TasksyncServer()
    server.start()
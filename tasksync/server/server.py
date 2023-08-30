from __future__ import annotations

import os
import json
import logging
import pickle
import socket
import sys

from tasksync.server.const import (
    SOCKET_PATH,
    SERVER_TIMEOUT,
    CONNECTION_TIMEOUT,
    MAX_BUFFER_SIZE
)

from tasksync.todoist import TodoistSync
from tasksync.translator import update_taskwarrior

class TasksyncServer:

    def __init__(self, 
                 socket_path : str = SOCKET_PATH,
                 server_timeout: int = SERVER_TIMEOUT,
                 debug : bool = False,
    ):
        self.socket_path = socket_path
        self.server_timeout = server_timeout
        self._sync = TodoistSync(basedir=os.path.join(os.environ['HOME'], '.todoist'))

        # Setup logger
        self.logger = logging.getLogger('tasksync')
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('{asctime} | {levelname:<8s} | {name} | {message}', style='{')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.debug('Starting Tasksync server')
        self.logger.setLevel(logging.DEBUG)

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

    def receive(self):
        connection, client_address = self.server.accept()
        self.logger.debug('Connection received')
        connection.settimeout(CONNECTION_TIMEOUT)
        try:
            # Get payload size
            payload_bytes = connection.recv(8)
            payload_bytes = int.from_bytes(payload_bytes, 'little', signed=False)
            self.logger.debug('payload size: {} bytes'.format(payload_bytes))
            # Receive data from the client
            chunks = []
            recd_bytes = 0
            while recd_bytes < payload_bytes:
                chunk = connection.recv(min(payload_bytes - recd_bytes, MAX_BUFFER_SIZE))
                if not chunk:
                    break
                chunks.append(chunk)
                recd_bytes += len(chunk)
            data = b''.join(chunks)
            connection.sendall(recd_bytes.to_bytes(8, 'little', signed=False))
            connection.close()
        except socket.error as err:
            connection.close()
            raise err
        
        # Append to list of commands needing to run
        self._sync.api.commands.extend(pickle.loads(data))
        return

    def stop(self):
        os.unlink(self.socket_path)
        return

    def sync(self):
        if len(self._sync.api.commands) > 0:
            # Push
            self.logger.debug('Syncing to Todoist')
            self.logger.debug('\n{}'.format(json.dumps(self._sync.api.commands, indent=2)))
            res = self._sync.api.push()

            # Check to see if any item_add commands were included
            # (in this case we need to update Taskwarrior)
            taskwarrior_ids = [x.get('temp_id') for x in self._sync.api.commands if x['type'] == 'item_add']
            if len(taskwarrior_ids) > 0:
                self.logger.debug('Updating Taskwarrior')
                update_taskwarrior(res, taskwarrior_ids)
            
            # Clean up
            self._sync.api.pull()
            self.logger.debug('Done')
            self._sync.api.commands = []
        return


if __name__ == '__main__':
    server = TasksyncServer()
    server.start()
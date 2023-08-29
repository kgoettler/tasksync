import os
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

class TasksyncServer:

    def __init__(self, 
                 socket_path : str = SOCKET_PATH,
                 server_timeout: int = SERVER_TIMEOUT
    ):
        self.socket_path = socket_path
        self.server_timeout = server_timeout

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
        except socket.error as err:
            connection.close()
            raise err
        
        # Append to list of commands needing to run
        self.commands.append(pickle.loads(data))
        return

    def stop(self):
        os.unlink(self.socket_path)
        return

    def sync(self):
        self.logger.debug('Syncing to Todoist')
        return


if __name__ == '__main__':
    server = TasksyncServer()
    server.start()
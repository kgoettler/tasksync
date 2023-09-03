import os
import socket
import pickle

from server.const import (
    SOCKET_PATH,
    CONNECTION_TIMEOUT,
)

class TasksyncClient:

    def __init__(self, socket_path=SOCKET_PATH):
        self.socket_path = socket_path
        if not os.path.exists(self.socket_path):
            raise FileNotFoundError(
                'No socket found at {}. Is the server running?'.format(self.socket_path)
            )

    def connect(self):
        self.client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.client.connect(self.socket_path)
        self.client.settimeout(CONNECTION_TIMEOUT)
        return

    def send(self, data):
        payload = pickle.dumps(data)
        data_size = len(payload).to_bytes(8, 'little', signed=False)

        # Send
        self.client.sendall(data_size)
        self.client.sendall(payload)
        recv_size = self.client.recv(8)
        return recv_size == data_size
    
    def close(self):
        self.client.close()
        return
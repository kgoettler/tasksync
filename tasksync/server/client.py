import os
import socket
import pickle

from tasksync.server import (
    SOCKET_PATH,
    CONNECTION_TIMEOUT,
    send_data,
    receive_data,
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
    
    def on_add(self, task_str: str) -> str:
        data = {
            'type': 'on-add',
            'args': [
                task_str,
            ]
        }
        return self.send(data)
    
    def on_modify(self, task_str_old : str, task_str_new : str) -> str:
        data = {
            'type': 'on-modify',
            'args': [
                task_str_old,
                task_str_new,
            ]
        }
        return self.send(data)

    def send(self, data) -> str:

        # Send data
        send_data(self.client, data)
        
        # Receive feedback string
        feedback = receive_data(self.client)

        return feedback
   
    def close(self):
        self.client.close()
        return
    
if __name__ == '__main__':
    client = TasksyncClient()
    client.connect()
    data = {'name': 'ken'}
    res = client.send(data)
    print(res)
    client.close()
import socket
import pickle
from typing import Any

SOCKET_PATH = '/tmp/tasksync'
SERVER_TIMEOUT = 10
CONNECTION_TIMEOUT = 5
MAX_BUFFER_SIZE = 1024


def send_ack(connection : socket.socket):
    connection.sendall(bool(True).to_bytes(1, 'little'))
    return 

def receive_ack(connection : socket.socket):
    recv_ok = connection.recv(1)
    if not bool.from_bytes(recv_ok, 'little'):
        raise ConnectionError('Did not receive OK from tasksync.server')
    return 

def send_data(connection : socket.socket, data : Any):
    data_bytes = pickle.dumps(data)
    data_size = len(data_bytes).to_bytes(8, 'little', signed=False)

    # Send message size
    connection.sendall(data_size)
    receive_ack(connection)
    
    # Send message
    connection.sendall(data_bytes)
    receive_ack(connection)
    return

def receive_data(connection : socket.socket) -> Any:
    data_size_b = connection.recv(8)
    data_size = int.from_bytes(data_size_b, 'little', signed=False)
    send_ack(connection)
    
    # Receive data from the client
    chunks = []
    recd_bytes = 0
    while recd_bytes < data_size:
        chunk = connection.recv(min(data_size - recd_bytes, MAX_BUFFER_SIZE))
        if not chunk:
            break
        chunks.append(chunk)
        recd_bytes += len(chunk)
    send_ack(connection)
    return pickle.loads(b''.join(chunks))
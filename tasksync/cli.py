#!/usr/bin/env python3

from __future__ import annotations

from os.path import basename, dirname, exists, join
import argparse
import os
import signal
import socket
import subprocess
import sys

import tasksync
from server import SOCKET_PATH
    
PIDFILE = join(os.environ["HOME"], 'tasksync.pid')
LOGFILE = join(os.environ["HOME"], 'tasksync.log')

def check_tasksync_running() -> bool:
    try:
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.connect(SOCKET_PATH)
    except ConnectionRefusedError:
        return False
    return True

def get_tasksync_pid() -> int | None:
    if not exists(PIDFILE):
        return
    with open(PIDFILE, 'r') as f:
        pid = f.read()
        if pid == '':
            return None
        return int(pid)

def start() -> int:
    '''
    Start the Tasksync server
    '''
    if _ := get_tasksync_pid():
        print('tasksync is already running')
        return 1
    logfile = open(LOGFILE, 'w+')
    res = subprocess.Popen([
        'python3',
        '{}/server/server.py'.format(dirname(tasksync.__file__))
    ], stdout=logfile)
    with open(PIDFILE, 'w') as f:
        f.write('{}'.format(res.pid))
    print('tasksync started')
    return 0

def stop() -> int:
    '''
    Stop the Tasksync server
    '''
    if pid := get_tasksync_pid():
        try:
            os.kill(pid, signal.SIGTERM)
            print('tasksync stopped')
        except ProcessLookupError:
            print('tasksync is not running')
        if exists(PIDFILE):
            os.remove(PIDFILE)
        return 0
    else:
        print('tasksync is not running')
        return 1
    
def status() -> int:
    '''
    Print whether the Tasksync server is running
    '''
    if pid := get_tasksync_pid():
        print('tasksync is running with pid {}'.format(pid))
    else:
        print('tasksync is not running')
    return 0


def pull() -> int:
    '''
    Run a complete sync of Todoist -> Taskwarrior
    '''
    raise NotImplementedError('pull is not yet implemented')

def push() -> int:
    '''
    Run a complete sync of Taskwarrior -> Todoist'''
    raise NotImplementedError('push is not yet implemented')

def main():
    parser = argparse.ArgumentParser(
        description='tasksync: start/stop/status of the tasksync server',
    )
    parser.add_argument(
        'cmd',
        type=str,
        help='action to perform (start | stop | status)',
    )
    args = parser.parse_args()
    if args.cmd == 'start':
        res = start()
    elif args.cmd == 'stop':
        res = stop()
    elif args.cmd == 'status':
        res = status()
    else:
        raise RuntimeError('{} not a recognized command'.format(args.cmd))
    sys.exit(res)

if __name__ == '__main__':
    main()

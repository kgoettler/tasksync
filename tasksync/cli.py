#!/usr/bin/env python3

from __future__ import annotations

from os.path import basename, dirname, exists, join
import argparse
import os
import signal
import socket
import subprocess
import sys

from tasksync.server.client import TasksyncClient

SOCKET_PATH = '/tmp/tasksync'
PIDFILE = join(os.environ["HOME"], 'tasksync.pid')
LOGFILE = join(os.environ["HOME"], 'tasksync.log')

class TasksyncCLI:
    client : TasksyncClient

    def __init__(self):
        self.client = TasksyncClient()

    def parse_args(self):
        parser = argparse.ArgumentParser(
            description='tasksync: start/stop/status of the tasksync server',
        )
        parser.add_argument(
            'cmd',
            type=str,
            help='action to perform (start | stop | status)',
        )
        return parser.parse_args()

    def get_server_pid(self) -> int | None:
        try:
            self.client.connect()
            pid = self.client.status()
            self.client.close()
            return int(pid)
        except:
            return None

    def start(self) -> int:
        if self.get_server_pid():
            print('tasksync is already running')
            return 1
        logfile = open(LOGFILE, 'w+')
        res = subprocess.Popen([
            'python3',
            '-m',
            'tasksync.server.server',
        ], stdout=logfile)
        print('tasksync started')
        return 0
    

    def stop(self) -> int:
        if self.get_server_pid():
            self.client.connect()
            self.client.stop()
            self.client.close()
            print('tasksync stopped')
            return 0
        else:
            print('tasksync is not running')
            return 1
    
    def status(self) -> int:
        if pid := self.get_server_pid():
            print('tasksync is running with pid {}'.format(pid))
        else:
            print('tasksync is not running')
        return 0

def main():
    cli = TasksyncCLI()
    args = cli.parse_args()
    if args.cmd == 'start':
        res = cli.start()
    elif args.cmd == 'stop':
        res = cli.stop()
    elif args.cmd == 'status':
        res = cli.status()
    else:
        raise RuntimeError('{} not a recognized command'.format(args.cmd))
    sys.exit(res)

if __name__ == '__main__':
    main()

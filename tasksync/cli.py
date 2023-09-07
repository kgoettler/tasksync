#!/usr/bin/env python3

from __future__ import annotations

from os.path import basename, dirname, exists, join
import argparse
import os
import signal
import socket
import subprocess
import sys

from tasksync import __version__
from tasksync.server.client import TasksyncClient

SOCKET_PATH = '/tmp/tasksync'
PIDFILE = join(os.environ["HOME"], 'tasksync.pid')
LOGFILE = join(os.environ["HOME"], 'tasksync.log')

class TasksyncCLI:
    _commands = [
        'start',
        'stop',
        'status',
    ]
    client : TasksyncClient

    def __init__(self):
        self.client = TasksyncClient()

        # Setup argument parser
        self.parser = argparse.ArgumentParser(
            description='tasksync: start/stop/status of the tasksync server',
        )
        self.parser.add_argument(
            '-v',
            '--version',
            action='store_true',
            default=False,
            help='print version',
        )
        _subparsers = self.parser.add_subparsers()
        subparsers = []
        for cmd in self._commands:
            subparsers.append(_subparsers.add_parser(
                cmd,
                help='{} the tasksync service'.format(cmd),
            ))
            subparsers[-1].set_defaults(func=getattr(self, cmd))

    def parse_args(self):
        return self.parser.parse_args()

    def get_server_pid(self) -> int | None:
        try:
            self.client.connect()
            pid = self.client.status()
            self.client.close()
            return int(pid)
        except Exception as _:
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
    if args.version:
        print(__version__)
    elif not hasattr(args, 'func'):
        cli.parser.print_help()
    else:
        sys.exit(args.func())
    sys.exit(0)

if __name__ == '__main__':
    main()

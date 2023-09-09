#!/usr/bin/env python3

from __future__ import annotations

from os.path import join
import argparse
import os
import sys

from tasksync import __version__
from tasksync.server.client import TasksyncClient
from tasksync.server.server import TasksyncServer
from tasksync.todoist.provider import TodoistProvider

SOCKET_PATH = "/tmp/tasksync"
PIDFILE = join(os.environ["HOME"], "tasksync.pid")
LOGFILE = join(os.environ["HOME"], "tasksync.log")


class TasksyncCLI:
    _commands = [
        "start",
        "stop",
        "status",
        "pull",
    ]
    client: TasksyncClient

    def __init__(self):
        self.client = TasksyncClient()

        # Setup argument parser
        self.parser = argparse.ArgumentParser(
            description="tasksync: start/stop/status of the tasksync server",
        )
        self.parser.add_argument(
            "-v",
            "--version",
            action="store_true",
            default=False,
            help="print version",
        )
        _subparsers = self.parser.add_subparsers()
        subparsers = []
        for cmd in self._commands:
            subparsers.append(
                _subparsers.add_parser(
                    cmd,
                    help="{} the tasksync service".format(cmd),
                )
            )
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
            print("tasksync is already running")
            return 1
        logfile = open(LOGFILE, "a+")

        # Do first fork
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError as e:
            print("fork #1 failed: %d (%s)" % (e.errno, e.strerror))
            sys.exit(1)

        os.chdir("/")
        os.setsid()
        os.umask(0)

        # Do second fork
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError as e:
            print("fork #2 failed: %d (%s)" % (e.errno, e.strerror))
            sys.exit(1)

        # redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        si = open("/dev/null", "r")
        so = logfile
        se = logfile
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

        pid = os.getpid()
        server = TasksyncServer()
        server.start()
        return 0

    def stop(self) -> int:
        if self.get_server_pid():
            self.client.connect()
            self.client.stop()
            self.client.close()
            print("tasksync stopped")
            return 0
        else:
            print("tasksync is not running")
            return 1

    def status(self) -> int:
        if pid := self.get_server_pid():
            print("tasksync is running with pid {}".format(pid))
            return 0
        else:
            print("tasksync is not running")
            return 1

    def pull(self) -> int:
        provider = TodoistProvider()
        provider.pull(full=True)
        return 0


def main():
    cli = TasksyncCLI()
    args = cli.parse_args()
    if args.version:
        print(__version__)
    elif not hasattr(args, "func"):
        cli.parser.print_help()
    else:
        sys.exit(args.func())
    sys.exit(0)


if __name__ == "__main__":
    main()

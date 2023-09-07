#!/usr/bin/env python3

import os
from os.path import basename, dirname, exists, join, splitext
import sys

# Ensure pip-installed tasksync isn't overridden by current directory
if 'tasksync' in os.listdir():
    cwd = os.getcwd()
    while cwd in sys.path:
        sys.path.remove(cwd)

import tasksync

hook_src = join(
    dirname(tasksync.__file__),
    'hooks',
)
hook_dest = join(
    os.environ.get('TASKDATA', join(os.environ['HOME'], '.task')),
    'hooks',
)

for hookfile in os.listdir(join(hook_src)):
    if not splitext(hookfile)[1] == '.py':
        continue
    link_src = join(hook_src, hookfile)
    link_dest = join(hook_dest, hookfile)
    if exists(link_dest):
        os.remove(link_dest)
    os.symlink(link_src, link_dest)

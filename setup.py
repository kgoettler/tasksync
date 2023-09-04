#!/usr/bin/env python

from setuptools import setup

DESCRIPTION = "tasksync - tool for syncing taskwarrior and todoist"
DISTNAME = 'tasksync'
MAINTAINER = 'Ken Goettler'
MAINTAINER_EMAIL = 'goettlek@gmail.com'
URL = 'https://www.kgoettler.com'
LICENSE = 'MIT License'
DOWNLOAD_URL = 'https://github.com/kgoettler/tasksync'
VERSION = '1.0'
PYTHON_REQUIRES = ">=3.9"
PY_MODULES = [
    'tasksync',
    'tasksync.server',
    'tasksync.taskwarrior',
    'tasksync.todoist',
]
CLASSIFIERS = [
    'Programming Language :: Python :: 3.9',
    'Operating System :: OS Independent',
]

setup(
    name=DISTNAME,
    author=MAINTAINER,
    author_email=MAINTAINER_EMAIL,
    maintainer=MAINTAINER,
    maintainer_email=MAINTAINER_EMAIL,
    description=DESCRIPTION,
    license=LICENSE,
    url=URL,
    version=VERSION,
    download_url=DOWNLOAD_URL,
    python_requires=PYTHON_REQUIRES,
    py_modules=PY_MODULES,
    classifiers=CLASSIFIERS,
    entry_points={
        'console_scripts': [
            'tasksync=tasksync.cli:main',
        ]
    },
)

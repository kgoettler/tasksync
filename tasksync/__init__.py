from os.path import dirname, join
with open(join(dirname(__file__), 'VERSION'), 'r') as f:
    __version__ = f.read().rstrip('\n')

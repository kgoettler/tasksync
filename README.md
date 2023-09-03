## tasksync

I love Taskwarrior but it doesn't have a mobile app. I love Todoist less, but it
has a mobile app and a well-documented API. This is a Python library to
facilitate syncing between the two.

Note: this is very much a WIP; I make no guarantees about the stability of the API or the scripts here, though I welcome any feedback or ideas!

## Setup

1. Store your Todoist API key as an environment variable

```bash
export TODOIST_API_KEY=0123456789abcdefg
```

2. Clone this repo, and install `tasksync` into your Python environment of choice

```bash
git clone 
python3 -m pip install tasksync
```

3.  Install hook scripts into your Taskwarrior hooks directory (by default this is `$HOME/.task/hooks`)

```bash
cp hooks/*.py $HOME/.task/hooks/
chmod +x $HOME/.task/hooks/on-add-todoist.py
chmod +x $HOME/.task/hooks/on-modify-todoist.py
```

## To Do

- [x] Support for adding, deleting, and modifying tasks
- [x] Implement unit tests
- [x] Support for due dates
- [x] Support for projects
- [ ] Formalize sync tools
- [ ] Support for annotations
- [ ] Support for subtasks
- [ ] Support for arbitrary UDAs
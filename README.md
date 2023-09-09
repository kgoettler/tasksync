## tasksync

Tasksync is a tool to keep Taskwarrior and Todoist in sync with each other.

## Setup

1. Store your Todoist API key as an environment variable. You can find this in the Todoist desktop or web applications in Settings -> Integrations -> Developer -> API Token.

```bash
export TODOIST_API_KEY=foobar123
```

2. Clone this repo, and install `tasksync` into your Python environment of choice

```bash
git clone git@github.com:kgoettler/tasksync.git
python3 -m pip install tasksync/
```

3.  Run `install_hooks.py` to install the supplied `on-add` and `on-modify` hook scripts into your Taskwarrior hooks directory:

```bash
python3 tasksync/install_hooks.py
```

**Note**: you may also need to update the shebang lines at the top of each script to point to a specific Python interpreter if you are using `conda`, `pyenv`, etc.

5. Start the tasksync daemon

```bash
tasksync start
```

6. If you wish to sync all of your existing tasks from Todoist into Taskwarrior, run the `pull` command

```bash
tasksync pull
```

## To Do

- [x] Support for adding, deleting, and modifying tasks
- [x] Support for due dates
- [x] Support for projects
- [x] Improved CLI for interacting with tasksync server
- [x] Implement sync tool (-> Taskwarrior)
- [ ] Implement sync tool (-> Todoist)
- [ ] Formalize logging by tasksync server

### Maybes

- [ ] Support for subtasks
- [ ] Support for annotations

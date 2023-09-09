## tasksync

Tasksync is a tool to keep Taskwarrior and Todoist in sync with each other.

## Setup

1. Store your Todoist API key as an environment variable. You can find this in the Todoist desktop or web applications in Settings -> Integrations -> Developer -> API Token.

```bash
echo "export TODOIST_API_KEY=foobar123" >> ~/.bash_profile
```

2. Install `tasksync` into your Python environment of choice and install the Taskwarrior hook scripts:

```bash
git clone git@github.com:kgoettler/tasksync.git
python3 -m pip install tasksync/
python3 tasksync/install_hooks.py
```

3. Run `tasksync start` to start the tasksync service. Now whenever tasks are created and/or updated in Taskwarrior, corresponding tasks will be created and/or updated in Todoist.

4. (Optional) Run `tasksync pull` to pull all existing tasks from Todoist into Taskwarrior.

## How it Works

Tasksync runs as a background service which receives notifications about newly
added or modified tasks from Taskwarrior and sends the corresponding updates to
Todoist. Tasksync receives notifications via Taskwarrior hook scripts, and sends updates to Todoist via the Todoist Sync API. Updates are not sent synchronously; Tasksync only sends updates to Todoist after 10 seconds have elapsed without any updates from Taskwarrior. This provides several benefits:

- Taskwarrior hooks are not blocked by network calls
  - Runtime with synchronous network calls: ~800ms
  - Runtime with tasksync: ~100ms
- Todoist Sync API calls can be batched
- Syncing can be disabled by simply shutting down the service

## Usage

Once the hook scripts are installed, the Tasksync service can be controlled via the `tasksync` CLI:

```bash
tasksync -h
usage: tasksync [-h] [-v] {start,stop,status,pull} ...

tasksync: start/stop/status of the tasksync server

positional arguments:
  {start,stop,status,pull}
    start               start the tasksync service
    stop                stop the tasksync service
    status              status the tasksync service
    pull                pull updates from Todoist into Taskwarrior

optional arguments:
  -h, --help            show this help message and exit
  -v, --version         print version
```

- `tasksync start` will start the background service
- `tasksync stop` will stop the background service
- `tasksync status` will indicate whether the background service is running
- `tasksync pull` will immediately sync changes from Todoist -> Taskwarrior

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

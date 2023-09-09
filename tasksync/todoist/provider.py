from __future__ import annotations

import uuid
import subprocess
from zoneinfo import ZoneInfo

from tasklib import Task, TaskWarrior

from tasksync.models import TasksyncDatetime
from tasksync.taskwarrior.models import (
    TaskwarriorTask,
    TaskwarriorPriority,
    TaskwarriorStatus,
)
from tasksync.todoist.api import (
    TodoistSync,
    TodoistSyncDataStore,
    TodoistSyncAPI,
)
from tasksync.todoist.models import TodoistSyncTask, TodoistSyncDue

TODOIST_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


class TodoistProvider:
    def __init__(self, store=None, api=None):
        self.commands = []
        self.store = TodoistSyncDataStore() if store is None else store
        self.api = TodoistSync(store=self.store) if api is None else api

    def on_add(self, task: TaskwarriorTask) -> tuple[str, str]:
        self.commands += TodoistProvider.add_item(task, self.store)
        feedback = "Todoist: item created"
        return task.to_taskwarrior(), feedback

    def on_modify(
        self, task_old: TaskwarriorTask, task_new: TaskwarriorTask
    ) -> tuple[str, str]:
        # If task doesn't have a todoist id just create it and move on
        if task_new.todoist is None:
            return self.on_add(task_new)[0], "Todoist: item created (did not exist)"

        # Record any supported updates
        actions = []
        commands = []
        if ops := TodoistProvider.update_item(task_old, task_new, self.store):
            commands += ops
            actions.append("updated")
        if ops := TodoistProvider.move_item(task_old, task_new, self.store):
            commands += ops
            actions.append("moved")
        if ops := TodoistProvider.delete_item(task_old, task_new, self.store):
            commands += ops
            actions.append("deleted")
        elif ops := TodoistProvider.complete_item(task_old, task_new, self.store):
            commands += ops
            actions.append("completed")
        elif ops := TodoistProvider.uncomplete_item(task_old, task_new, self.store):
            commands += ops
            actions.append("uncompleted")
        if len(commands) == 0:
            feedback = "Todoist: update not required"
        else:
            if len(actions) == 1:
                feedback = "Todoist: item {}".format(actions[0])
            elif len(actions) == 2:
                feedback = "Todoist: item {} and {}".format(*actions)
            else:
                feedback = "Todoist: item {}, and {}".format(
                    ", ".join(actions[0:-1]),
                    actions[-1],
                )
            self.commands += commands
        return task_new.to_taskwarrior(exclude_id=True), feedback

    def pull(self, full=False) -> None:
        resource_types = None if full else ["items"]
        _ = self.api.pull(resource_types=resource_types)
        tw = TaskWarrior()
        tw.overrides.update({"hooks": "off"})

        # Get only those taskwarrior tasks with Todoist IDs
        known_ids = set((task["todoist"] for task in tw.tasks))
        if None in known_ids:
            known_ids.remove(None)
        for todoist_task in self.store.find_all("items"):
            if todoist_task["id"] in known_ids:
                # Update from todoist
                task = update_from_todoist(tw, todoist_task, self.store)
                if task:
                    task.save()
            # Else if task does not exist, but is not deleted or completed
            elif (
                not todoist_task["is_deleted"] and todoist_task["completed_at"] is None
            ):
                task = create_from_todoist(
                    tw,
                    todoist_task,
                    self.store,
                )
                task.save()
        return

    def push(self) -> None:
        res = self.api.push(commands=self.commands)

        # Check to see if any item_add commands were included
        # (in this case we need to update Taskwarrior with the IDs)
        new_uuids = [x.get("temp_id") for x in self.commands if x["type"] == "item_add"]
        if len(new_uuids) > 0:
            TodoistProvider.update_taskwarrior(res, new_uuids)

        # Clear out commands
        self.commands.clear()
        return

    @property
    def updated(self):
        return len(self.commands) > 0

    @staticmethod
    def add_item(task: TaskwarriorTask, store: TodoistSyncDataStore) -> list:
        ops = []
        kwargs = {}
        if task.project:
            if project := store.find("projects", name=task.project):
                kwargs["project_id"] = project["id"]
            else:
                temp_id = str(uuid.uuid4())
                ops.append(
                    TodoistSyncAPI.create_project(name=task.project, temp_id=temp_id)
                )
                kwargs["project_id"] = temp_id
        if task.due:
            kwargs["due"] = TodoistProvider.date_from_taskwarrior(
                task.due,
                task.timezone,  # type: ignore
            )
        if task.priority:
            kwargs["priority"] = task.priority.value + 1  # type: ignore
        if len(task.tags) > 0:
            kwargs["labels"] = task.tags  # type: ignore
        ops.append(
            TodoistSyncAPI.add_item(
                task.description,
                str(task.uuid),
                **kwargs,
            )
        )
        return ops

    @staticmethod
    def update_item(
        task_old: TaskwarriorTask,
        task_new: TaskwarriorTask,
        store: TodoistSyncDataStore,
    ) -> list:
        ops = []
        kwargs = {}

        # Description
        if task_old.description != task_new.description:
            kwargs["content"] = task_new.description

        # Due date
        if TodoistProvider._check_update(task_old, task_new, "due"):
            kwargs["due"] = TodoistProvider.date_from_taskwarrior(
                task_new.due,  # type: ignore
                task_new.timezone,  # type: ignore
            )
        elif TodoistProvider._check_remove(task_old, task_new, "due"):
            kwargs["due"] = None

        # Priority
        if TodoistProvider._check_update(task_old, task_new, "priority"):
            kwargs["priority"] = task_new.priority.value + 1  # type: ignore
        elif TodoistProvider._check_remove(task_old, task_new, "priority"):
            kwargs["priority"] = 1

        # Labels
        if TodoistProvider._check_update(task_old, task_new, "tags"):
            kwargs["labels"] = task_new.tags

        # Build payload
        if len(kwargs) > 0:
            ops.append(
                TodoistSyncAPI.modify_item(
                    task_new.todoist,
                    **kwargs,
                )
            )
        return ops

    @staticmethod
    def move_item(
        task_old: TaskwarriorTask,
        task_new: TaskwarriorTask,
        store: TodoistSyncDataStore,
    ) -> list:
        ops = []
        kwargs = {}

        # Project
        project_id = None
        # (0, 1) or (1, 1)
        if task_new.project is not None:
            if project := store.find("projects", name=task_new.project):
                project_id = project["id"]
                if task_old.project != task_new.project:
                    kwargs["project_id"] = project_id
            else:
                # Project does not exist -- we need to create it
                # Use temporary uuid so we can identify it in successive calls (prn)
                project_id = str(uuid.uuid4())
                ops.append(
                    TodoistSyncAPI.create_project(
                        name=task_new.project,
                        temp_id=project_id,
                    )
                )  # type: ignore
                kwargs["project_id"] = project_id
        else:
            if project := store.find("projects", name="Inbox"):
                project_id = project["id"]
                kwargs["project_id"] = project_id
            else:
                raise RuntimeError(
                    "Attempting to move task to Inbox, but Inbox project not found in data store!"  # noqa: E501
                )

        # Now do the same thing for the section
        if task_new.section is not None:
            # Section was updated
            if section := store.find(
                "sections", name=task_new.section, project_id=project_id
            ):
                # if it exists in this project, supply section_id as argument
                # instead of project_id
                section_id = section["id"]
                kwargs["section_id"] = section["id"]
                if "project_id" in kwargs:
                    del kwargs["project_id"]
            else:
                # Section does not exist -- we need to create it
                section_id = str(uuid.uuid4())
                ops.append(
                    TodoistSyncAPI.create_section(
                        name=task_new.section,
                        temp_id=section_id,
                        project_id=project_id,
                    )
                )  # type: ignore
                kwargs["section_id"] = section_id
        elif task_old.section is not None:
            # From API docs:
            # > to move an item from a section to no section, just use the
            # > project_id parameter, with the project it currently belongs to as a
            # > value.
            kwargs["project_id"] = project_id

        if len(kwargs) > 0:
            ops.append(TodoistSyncAPI.move_item(task_new.todoist, **kwargs))
        return ops

    @staticmethod
    def delete_item(
        task_old: TaskwarriorTask,
        task_new: TaskwarriorTask,
        store: TodoistSyncDataStore,
    ) -> list:
        ops = []
        if (
            task_old.status != TaskwarriorStatus.DELETED
            and task_new.status == TaskwarriorStatus.DELETED
        ):
            data = {
                "type": "item_delete",
                "uuid": str(uuid.uuid4()),
                "args": {
                    "id": str(task_new.todoist),
                },
            }
            ops.append(data)
        return ops

    @staticmethod
    def complete_item(
        task_old: TaskwarriorTask,
        task_new: TaskwarriorTask,
        store: TodoistSyncDataStore,
    ) -> list:
        ops = []
        if (
            task_old.status != TaskwarriorStatus.COMPLETED
            and task_new.status == TaskwarriorStatus.COMPLETED
        ):
            ops.append(
                TodoistSyncAPI.complete_item(
                    task_new.todoist,
                    date_completed=None
                    if task_new.end is None
                    else task_new.end.strftime(TODOIST_DATETIME_FORMAT),
                )
            )
        return ops

    @staticmethod
    def uncomplete_item(
        task_old: TaskwarriorTask,
        task_new: TaskwarriorTask,
        store: TodoistSyncDataStore,
    ) -> list:
        ops = []
        if (
            task_old.status == TaskwarriorStatus.COMPLETED
            and task_new.status != TaskwarriorStatus.COMPLETED
        ):
            ops.append(
                TodoistSyncAPI.uncomplete_item(
                    task_new.todoist,  # type: ignore
                )
            )
        return ops

    @staticmethod
    def date_from_taskwarrior(date: TasksyncDatetime, timezone: str) -> TodoistSyncDue:
        out = TodoistSyncDue(
            {
                "timezone": timezone,
                "is_recurring": False,
            }
        )
        due_datetime = date.astimezone(ZoneInfo(timezone))
        if due_datetime.hour == 0 and due_datetime.minute == 0:
            out["date"] = date.strftime("%Y-%m-%d")
        else:
            out["date"] = date.strftime(TODOIST_DATETIME_FORMAT)
        return out

    @staticmethod
    def update_taskwarrior(sync_res, taskwarrior_uuids):
        """
        Update Taskwarrior with Todoist IDs returned by the Sync API

        Note: this only works if you use the taskwarrior UUID as the temp_id in your
        API calls!
        """
        for taskwarrior_uuid in taskwarrior_uuids:
            if todoist_id := sync_res.get("temp_id_mapping", {}).get(taskwarrior_uuid):
                command = [
                    "task",
                    "rc.hooks=off",  # bypass hooks
                    taskwarrior_uuid,
                    "modify",
                    "todoist={}".format(str(todoist_id)),
                ]
                _ = subprocess.run(
                    command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
        return

    @staticmethod
    def _check_update(
        task_old: TaskwarriorTask, task_new: TaskwarriorTask, attr: str
    ) -> bool:
        oldval = getattr(task_old, attr)
        newval = getattr(task_new, attr)
        return newval is not None and (oldval is None or (oldval != newval))

    @staticmethod
    def _check_remove(
        task_old: TaskwarriorTask, task_new: TaskwarriorTask, attr: str
    ) -> bool:
        oldval = getattr(task_old, attr)
        newval = getattr(task_new, attr)
        return oldval is not None and newval is None


def create_from_todoist(
    tw: TaskWarrior, todoist_task: TodoistSyncTask, store: TodoistSyncDataStore
) -> Task:
    out: Task = Task(
        tw,
        description=todoist_task["content"],
    )
    # Project ID
    if project_id := todoist_task["project_id"]:
        if project := store.find("projects", id=project_id):
            out["project"] = project["name"]

    # Priority
    if todoist_task["priority"] is not None:
        out["priority"] = convert_priority(todoist_task["priority"])

    # Labels
    if len(todoist_task["labels"]) > 0:
        out["tags"] = set(todoist_task["labels"])

    # Due date
    if todoist_task["due"] is not None:
        if due := TasksyncDatetime.from_todoist(todoist_task["due"]):
            out["due"] = out.deserialize_due(due.to_taskwarrior())

    # Section
    if section_id := todoist_task["section_id"]:
        if section := store.find("sections", id=section_id):
            out["section"] = section["name"]

    out["todoist"] = todoist_task["id"]

    return out


def update_from_todoist(
    tw: TaskWarrior, todoist_task: TodoistSyncTask, store: TodoistSyncDataStore
) -> Task | None:
    task = tw.tasks.get(todoist=todoist_task["id"])

    # Ignore deleted tasks
    if task.deleted and todoist_task["is_deleted"]:
        return

    # Update status
    # - Close completed tasks
    if not task.completed and todoist_task["completed_at"] is not None:
        task.done()
        # task._data['end'] = TasksyncDatetime.from_todoist(todoist_task['completed_at']).to_taskwarrior()  # noqa: E501

    # Update description
    if task["description"] != todoist_task["content"]:
        task["description"] = todoist_task["content"]

    # Update project
    if project := store.find("projects", id=todoist_task["project_id"]):
        if task["project"] != project["name"]:
            task["project"] = project["name"]

    # Update priority
    tw_priority = (
        0 if task["priority"] is None else TaskwarriorPriority[task["priority"]].value
    )
    if (tw_priority + 1) != todoist_task["priority"]:
        task["priority"] = convert_priority(todoist_task["priority"])

    # Update tags
    if task["tags"] != set(todoist_task["labels"]):
        task["tags"] = set(todoist_task["labels"])

    # Update due
    tw_due = None if task["due"] is None else task.serialize_due(task["due"])
    todoist_due = todoist_task["due"]
    if todoist_due is not None and (
        todoist_due := TasksyncDatetime.from_todoist(todoist_due)
    ):
        todoist_due = todoist_due.to_taskwarrior()
    if tw_due != todoist_due:
        task["due"] = None if todoist_due is None else task.deserialize_due(todoist_due)

    # Update section
    if section := store.find("sections", id=todoist_task["section_id"]):
        if task["section"] != section["name"]:
            task["section"] = section["name"]

    # Update todoist uda
    task["todoist"] = todoist_task["id"]
    return task


def convert_labels(labels: list[str]) -> set:
    return set(labels)


def convert_priority(priority: int):
    priorities = [None, "L", "M", "H"]
    return priorities[priority - 1]

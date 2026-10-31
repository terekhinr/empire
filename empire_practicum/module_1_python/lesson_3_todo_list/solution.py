"""Урок 1.3 — Менеджер задач (To-Do List).

Реализуй класс TodoList самостоятельно.
"""


class TodoList:
    def __init__(self, filepath: str):
        # TODO: сохрани путь, загрузи файл или начни с []
        pass

    def add(self, title: str) -> dict:
        # TODO: добавь задачу, сохрани, верни dict
        pass

    def complete(self, task_id: int) -> bool:
        # TODO: отметь done=True
        pass

    def remove(self, task_id: int) -> bool:
        # TODO: удали задачу
        pass

    def list_tasks(self) -> list:
        # TODO: верни список задач
        pass

    def save(self) -> None:
        # TODO: запиши self.tasks в JSON
        pass

    def load(self) -> None:
        # TODO: прочитай JSON в self.tasks
        pass

"""Автопроверка урока 1.3 — To-Do List."""

import importlib.util
import json
from pathlib import Path

import pytest

SOLUTION_PATH = Path(__file__).parent / "solution.py"


def _load_solution():
    spec = importlib.util.spec_from_file_location("lesson3_solution", SOLUTION_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def TodoList():
    mod = _load_solution()
    assert hasattr(mod, "TodoList"), "В solution.py должен быть класс TodoList"
    return mod.TodoList


def test_add_and_list(TodoList, tmp_path):
    path = tmp_path / "todos.json"
    todo = TodoList(str(path))
    task = todo.add("Купить молоко")
    assert task["title"] == "Купить молоко"
    assert task["done"] is False
    assert task["id"] == 1
    assert len(todo.list_tasks()) == 1


def test_ids_increment(TodoList, tmp_path):
    path = tmp_path / "todos.json"
    todo = TodoList(str(path))
    t1 = todo.add("A")
    t2 = todo.add("B")
    assert t1["id"] == 1
    assert t2["id"] == 2


def test_complete(TodoList, tmp_path):
    path = tmp_path / "todos.json"
    todo = TodoList(str(path))
    task = todo.add("Сделать ДЗ")
    assert todo.complete(task["id"]) is True
    assert todo.list_tasks()[0]["done"] is True
    assert todo.complete(999) is False


def test_remove(TodoList, tmp_path):
    path = tmp_path / "todos.json"
    todo = TodoList(str(path))
    task = todo.add("Временная")
    assert todo.remove(task["id"]) is True
    assert todo.list_tasks() == []
    assert todo.remove(1) is False


def test_persistence(TodoList, tmp_path):
    path = tmp_path / "todos.json"
    todo = TodoList(str(path))
    todo.add("Навсегда")
    # Новый экземпляр должен прочитать файл
    todo2 = TodoList(str(path))
    tasks = todo2.list_tasks()
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Навсегда"
    # Файл действительно JSON
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(raw, list)

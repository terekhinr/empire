"""Автопроверка урока 2.1 — Эхо-бот."""

import importlib.util
from pathlib import Path

import pytest

SOLUTION_PATH = Path(__file__).parent / "solution.py"


def _load_solution():
    spec = importlib.util.spec_from_file_location("m2_l1_solution", SOLUTION_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def sol():
    return _load_solution()


def test_echo_text(sol):
    assert sol.echo_text("привет") == "привет"
    assert sol.echo_text("Hello") == "Hello"


def test_echo_none_and_empty(sol):
    assert sol.echo_text(None) == "Я понимаю только текст 📝"
    assert sol.echo_text("") == "Пустое сообщение"


def test_handle_start(sol):
    reply = sol.handle_command("/start")
    assert reply is not None
    assert "эхо-бот" in reply.lower() or "Empire" in reply


def test_handle_help(sol):
    reply = sol.handle_command("/help")
    assert reply is not None
    assert "/start" in reply and "/help" in reply


def test_handle_not_command(sol):
    assert sol.handle_command("просто текст") is None


def test_build_reply(sol):
    assert "эхо-бот" in sol.build_reply("/start").lower() or "Empire" in sol.build_reply("/start")
    assert sol.build_reply("ping") == "ping"
    assert sol.build_reply(None) == "Я понимаю только текст 📝"

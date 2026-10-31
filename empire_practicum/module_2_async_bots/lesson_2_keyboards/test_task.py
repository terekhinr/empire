"""Автопроверка урока 2.2 — Клавиатуры."""

import importlib.util
from pathlib import Path

import pytest

SOLUTION_PATH = Path(__file__).parent / "solution.py"


def _load_solution():
    spec = importlib.util.spec_from_file_location("m2_l2_solution", SOLUTION_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def sol():
    return _load_solution()


def test_reply_menu(sol):
    assert sol.build_reply_menu(["A", "B"]) == [["A"], ["B"]]
    assert sol.build_reply_menu([]) == []


def test_inline_services(sol):
    services = {"service_banya": "Баня", "service_massage": "Массаж"}
    result = sol.build_inline_services(services)
    assert result == [
        {"text": "Баня", "callback_data": "service_banya"},
        {"text": "Массаж", "callback_data": "service_massage"},
    ]


def test_parse_callback_service(sol):
    assert sol.parse_callback("service:banya") == {"type": "service", "value": "banya"}


def test_parse_callback_confirm(sol):
    assert sol.parse_callback("confirm:yes") == {"type": "confirm", "value": "yes"}
    assert sol.parse_callback("confirm:no") == {"type": "confirm", "value": "no"}


def test_parse_callback_unknown(sol):
    assert sol.parse_callback("foo") == {"type": "unknown", "value": "foo"}

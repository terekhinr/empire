"""Автопроверка урока 2.3 — FSM Анкета."""

import importlib.util
from pathlib import Path

import pytest

SOLUTION_PATH = Path(__file__).parent / "solution.py"


def _load_solution():
    spec = importlib.util.spec_from_file_location("m2_l3_solution", SOLUTION_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def LeadFormFSM():
    mod = _load_solution()
    assert hasattr(mod, "LeadFormFSM")
    return mod.LeadFormFSM


def test_start(LeadFormFSM):
    fsm = LeadFormFSM()
    msg = fsm.start()
    assert "зовут" in msg.lower()
    assert fsm.current_state() == "name"
    assert fsm.get_data() == {} or all(v in (None, "") for v in fsm.get_data().values())


def test_happy_path(LeadFormFSM):
    fsm = LeadFormFSM()
    fsm.start()
    r1 = fsm.process("Иван")
    assert r1["ok"] is True
    assert fsm.current_state() == "phone"
    r2 = fsm.process("+7 999 123-45-67")
    assert r2["ok"] is True
    assert fsm.current_state() == "service"
    r3 = fsm.process("Баня")
    assert r3["ok"] is True
    assert fsm.current_state() == "done"
    data = fsm.get_data()
    assert data["name"] == "Иван"
    assert "999" in "".join(ch for ch in data["phone"] if ch.isdigit()) or "999" in data["phone"]
    assert data["service"] == "Баня"
    assert "Иван" in r3["message"]


def test_short_phone(LeadFormFSM):
    fsm = LeadFormFSM()
    fsm.start()
    fsm.process("Мария")
    r = fsm.process("123")
    assert r["ok"] is False
    assert fsm.current_state() == "phone"
    assert "телефон" in r["message"].lower() or "короткий" in r["message"].lower()


def test_process_without_start(LeadFormFSM):
    fsm = LeadFormFSM()
    r = fsm.process("что угодно")
    assert r["ok"] is False
    assert "start" in r["message"].lower()


def test_restart_clears_data(LeadFormFSM):
    fsm = LeadFormFSM()
    fsm.start()
    fsm.process("Алексей")
    fsm.start()
    assert fsm.current_state() == "name"
    data = fsm.get_data()
    assert data.get("name") in (None, "",) or "name" not in data

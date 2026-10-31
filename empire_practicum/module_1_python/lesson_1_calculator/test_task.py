"""Автопроверка урока 1.1 — Калькулятор."""

import importlib.util
from pathlib import Path

import pytest

SOLUTION_PATH = Path(__file__).parent / "solution.py"


def _load_solution():
    spec = importlib.util.spec_from_file_location("lesson1_solution", SOLUTION_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def calculate():
    mod = _load_solution()
    assert hasattr(mod, "calculate"), "В solution.py должна быть функция calculate"
    return mod.calculate


def test_addition(calculate):
    assert calculate(2, 3, "+") == 5
    assert calculate(-1, 5, "+") == 4


def test_subtraction(calculate):
    assert calculate(10, 4, "-") == 6
    assert calculate(0, 5, "-") == -5


def test_multiplication(calculate):
    assert calculate(3, 4, "*") == 12
    assert calculate(-2, 3, "*") == -6


def test_division(calculate):
    assert calculate(10, 2, "/") == 5
    assert calculate(9, 3, "/") == 3


def test_division_by_zero(calculate):
    assert calculate(5, 0, "/") == "Error: division by zero"


def test_unknown_operation(calculate):
    assert calculate(1, 1, "^") == "Error: unknown operation"
    assert calculate(1, 1, "plus") == "Error: unknown operation"

"""Автопроверка урока 1.2 — Анализатор текста."""

import importlib.util
from pathlib import Path

import pytest

SOLUTION_PATH = Path(__file__).parent / "solution.py"


def _load_solution():
    spec = importlib.util.spec_from_file_location("lesson2_solution", SOLUTION_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def sol():
    return _load_solution()


def test_count_words_basic(sol):
    assert sol.count_words("Hello world hello") == {"hello": 2, "world": 1}


def test_count_words_empty(sol):
    assert sol.count_words("") == {}
    assert sol.count_words("   ") == {}


def test_count_words_single(sol):
    assert sol.count_words("Python") == {"python": 1}


def test_word_count(sol):
    assert sol.word_count("one two three") == 3
    assert sol.word_count("") == 0
    assert sol.word_count("  a  b  ") == 2


def test_most_common_word(sol):
    assert sol.most_common_word("a b a c a") == "a"
    assert sol.most_common_word("") is None


def test_most_common_tie_allowed(sol):
    result = sol.most_common_word("x y x y")
    assert result in {"x", "y"}

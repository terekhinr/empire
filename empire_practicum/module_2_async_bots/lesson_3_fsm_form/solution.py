"""Урок 2.3 — FSM Анкета.

Реализуй класс LeadFormFSM самостоятельно.
"""


class LeadFormFSM:
    def __init__(self):
        # TODO: начальное состояние idle, пустые данные
        pass

    def start(self) -> str:
        # TODO: сброс и приглашение
        pass

    def current_state(self) -> str:
        # TODO: верни текущее состояние
        pass

    def process(self, text: str) -> dict:
        # TODO: обработай шаг анкеты
        pass

    def get_data(self) -> dict:
        # TODO: верни собранные поля
        pass

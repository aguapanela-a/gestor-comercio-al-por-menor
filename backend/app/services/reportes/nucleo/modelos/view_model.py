from typing import Any


class ViewModel:
    def __init__(self, values: dict[str, Any]) -> None:
        self.__dict__.update(values)

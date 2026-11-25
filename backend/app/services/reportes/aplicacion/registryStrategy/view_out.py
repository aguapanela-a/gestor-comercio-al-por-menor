from abc import ABC, abstractmethod
from typing import Any


class ViewOut(ABC):
    @abstractmethod
    def getViewOut(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def getEntityName(self) -> str:
        raise NotImplementedError

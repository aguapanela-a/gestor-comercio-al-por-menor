from abc import ABC, abstractmethod
from typing import Any


class OutPortViews(ABC):
    @abstractmethod
    def getView(self, entityName: str) -> list[dict[str, Any]]:
        raise NotImplementedError

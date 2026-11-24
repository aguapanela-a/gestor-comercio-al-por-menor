from abc import ABC, abstractmethod

from app.services.reportes.nucleo.modelos import (
    View1,
    View2,
    View3,
    View4,
    View5,
    View6,
    View7,
    View8,
    View9,
    View10,
)


class InPortViews(ABC):
    @abstractmethod
    def getView1(self) -> list[View1]:
        raise NotImplementedError

    @abstractmethod
    def getView2(self) -> list[View2]:
        raise NotImplementedError

    @abstractmethod
    def getView3(self) -> list[View3]:
        raise NotImplementedError

    @abstractmethod
    def getView4(self) -> list[View4]:
        raise NotImplementedError

    @abstractmethod
    def getView5(self) -> list[View5]:
        raise NotImplementedError

    @abstractmethod
    def getView6(self) -> list[View6]:
        raise NotImplementedError

    @abstractmethod
    def getView7(self) -> list[View7]:
        raise NotImplementedError

    @abstractmethod
    def getView8(self) -> list[View8]:
        raise NotImplementedError

    @abstractmethod
    def getView9(self) -> list[View9]:
        raise NotImplementedError

    @abstractmethod
    def getView10(self) -> list[View10]:
        raise NotImplementedError

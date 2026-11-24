from app.services.reportes.aplicacion.puertos_entrada import InPortViews
from app.services.reportes.aplicacion.puertos_salida import OutPortViews
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


class UseCaseViews(InPortViews):
    def __init__(self, out_port: OutPortViews) -> None:
        self._out_port = out_port

    def getView1(self) -> list[View1]:
        return [View1(row) for row in self._out_port.getView("VIEW1")]

    def getView2(self) -> list[View2]:
        return [View2(row) for row in self._out_port.getView("VIEW2")]

    def getView3(self) -> list[View3]:
        return [View3(row) for row in self._out_port.getView("VIEW3")]

    def getView4(self) -> list[View4]:
        return [View4(row) for row in self._out_port.getView("VIEW4")]

    def getView5(self) -> list[View5]:
        return [View5(row) for row in self._out_port.getView("VIEW5")]

    def getView6(self) -> list[View6]:
        return [View6(row) for row in self._out_port.getView("VIEW6")]

    def getView7(self) -> list[View7]:
        return [View7(row) for row in self._out_port.getView("VIEW7")]

    def getView8(self) -> list[View8]:
        return [View8(row) for row in self._out_port.getView("VIEW8")]

    def getView9(self) -> list[View9]:
        return [View9(row) for row in self._out_port.getView("VIEW9")]

    def getView10(self) -> list[View10]:
        return [View10(row) for row in self._out_port.getView("VIEW10")]

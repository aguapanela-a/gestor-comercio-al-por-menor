from collections.abc import Callable
from typing import TypeVar

from fastapi import APIRouter, Depends, HTTPException, status

from app.services.reportes.aplicacion.puertos_entrada import InPortViews
from app.services.reportes.infraestructura.adaptadores_entrada.dependencies import (
    get_use_case_views,
)
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

T = TypeVar("T")


class GetViewInAdapter:
    def __init__(self) -> None:
        self.router = APIRouter(tags=["Reportes"])
        self.router.add_api_route(
            "/view1", self.get_view1, methods=["GET"], response_model=None
        )
        self.router.add_api_route(
            "/view2", self.get_view2, methods=["GET"], response_model=None
        )
        self.router.add_api_route(
            "/view3", self.get_view3, methods=["GET"], response_model=None
        )
        self.router.add_api_route(
            "/view4", self.get_view4, methods=["GET"], response_model=None
        )
        self.router.add_api_route(
            "/view5", self.get_view5, methods=["GET"], response_model=None
        )
        self.router.add_api_route(
            "/view6", self.get_view6, methods=["GET"], response_model=None
        )
        self.router.add_api_route(
            "/view7", self.get_view7, methods=["GET"], response_model=None
        )
        self.router.add_api_route(
            "/view8", self.get_view8, methods=["GET"], response_model=None
        )
        self.router.add_api_route(
            "/view9", self.get_view9, methods=["GET"], response_model=None
        )
        self.router.add_api_route(
            "/view10", self.get_view10, methods=["GET"], response_model=None
        )

    @staticmethod
    def _execute(operation: Callable[[], T]) -> T:
        try:
            return operation()
        except NotImplementedError as error:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=str(error),
            ) from error

    def get_view1(
        self, use_case: InPortViews = Depends(get_use_case_views)
    ) -> list[View1]:
        return self._execute(use_case.getView1)

    def get_view2(
        self, use_case: InPortViews = Depends(get_use_case_views)
    ) -> list[View2]:
        return self._execute(use_case.getView2)

    def get_view3(
        self, use_case: InPortViews = Depends(get_use_case_views)
    ) -> list[View3]:
        return self._execute(use_case.getView3)

    def get_view4(
        self, use_case: InPortViews = Depends(get_use_case_views)
    ) -> list[View4]:
        return self._execute(use_case.getView4)

    def get_view5(
        self, use_case: InPortViews = Depends(get_use_case_views)
    ) -> list[View5]:
        return self._execute(use_case.getView5)

    def get_view6(
        self, use_case: InPortViews = Depends(get_use_case_views)
    ) -> list[View6]:
        return self._execute(use_case.getView6)

    def get_view7(
        self, use_case: InPortViews = Depends(get_use_case_views)
    ) -> list[View7]:
        return self._execute(use_case.getView7)

    def get_view8(
        self, use_case: InPortViews = Depends(get_use_case_views)
    ) -> list[View8]:
        return self._execute(use_case.getView8)

    def get_view9(
        self, use_case: InPortViews = Depends(get_use_case_views)
    ) -> list[View9]:
        return self._execute(use_case.getView9)

    def get_view10(
        self, use_case: InPortViews = Depends(get_use_case_views)
    ) -> list[View10]:
        return self._execute(use_case.getView10)

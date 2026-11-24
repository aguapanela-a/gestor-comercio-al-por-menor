from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.services.inventarios.alerts import router as alerts_router
from app.services.inventarios.stock import router as stock_router
from app.services.inventarios.transfers import router as transfers_router

router = APIRouter(dependencies=[Depends(get_current_user)])
router.include_router(alerts_router)
router.include_router(stock_router)
router.include_router(transfers_router)

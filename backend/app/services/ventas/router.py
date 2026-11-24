from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.services.ventas.customers import router as customers_router
from app.services.ventas.orders import router as orders_router
from app.services.ventas.payments import router as payments_router
from app.services.ventas.returns import router as returns_router

router = APIRouter(dependencies=[Depends(get_current_user)])
router.include_router(customers_router)
router.include_router(orders_router)
router.include_router(payments_router)
router.include_router(returns_router)

from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.services.compras.purchase_orders import router as purchase_orders_router
from app.services.compras.receipts import router as receipts_router
from app.services.compras.suppliers import router as suppliers_router

router = APIRouter(dependencies=[Depends(get_current_user)])
router.include_router(suppliers_router)
router.include_router(purchase_orders_router)
router.include_router(receipts_router)

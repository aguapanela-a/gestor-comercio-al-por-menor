from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.services.organizacion.branches import router as branches_router
from app.services.organizacion.warehouses import router as warehouses_router

router = APIRouter(dependencies=[Depends(get_current_user)])
router.include_router(branches_router)
router.include_router(warehouses_router)

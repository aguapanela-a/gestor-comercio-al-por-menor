from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.services.catalogo.categories import router as categories_router
from app.services.catalogo.products import router as products_router

router = APIRouter(dependencies=[Depends(get_current_user)])
router.include_router(categories_router)
router.include_router(products_router)

"""
Routes package initialization
"""

from fastapi import APIRouter
from .auth_routes import router as auth_router
from .admin_routes import router as admin_router
from .excel_routes import router as excel_router
from .approver_routes import router as approver_router
from .inspector_routes import router as inspector_router
from .researcher_routes import router as researcher_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(admin_router)
router.include_router(excel_router)
router.include_router(approver_router)
router.include_router(inspector_router)
router.include_router(researcher_router) 
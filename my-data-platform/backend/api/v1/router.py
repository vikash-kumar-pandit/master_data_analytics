from fastapi import APIRouter
from api.v1.endpoints.datasets import router as datasets_router
from api.v1.endpoints.analytics import router as analytics_router
from api.v1.endpoints.sharing import router as sharing_router
from api.v1.endpoints.schedules import router as schedules_router
from api.v1.endpoints.summaries import router as summaries_router

router = APIRouter()

router.include_router(datasets_router)
router.include_router(analytics_router)
router.include_router(sharing_router)
router.include_router(schedules_router)
router.include_router(summaries_router)

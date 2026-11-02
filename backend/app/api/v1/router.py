from fastapi import APIRouter
from app.api.v1 import ai_engine, auth, leads, listings, media, agencies, discovery, viewings, videos

router = APIRouter(prefix='/api/v1')
router.include_router(auth.router)
router.include_router(listings.router)
router.include_router(leads.router)
router.include_router(ai_engine.router)

router.include_router(media.router)
router.include_router(videos.router)

router.include_router(agencies.router)
router.include_router(discovery.router)
router.include_router(viewings.router)

"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes.adjustments import router as adjustments_router
from app.routes.discover import router as discover_router
from app.routes.discovery import router as discovery_router
from app.routes.itinerary import router as itinerary_router
from app.routes.plan import router as plan_router
from app.routes.preferences import router as preferences_router
from app.routes.sessions import router as sessions_router

app = FastAPI(title="Travel Planner API", version="0.1.0")


settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)

app.include_router(discover_router)
app.include_router(plan_router)
app.include_router(sessions_router)
app.include_router(discovery_router)
app.include_router(preferences_router)
app.include_router(itinerary_router)
app.include_router(adjustments_router)


@app.get("/health")
async def health() -> dict:
    """Liveness check — used by Docker/load balancer."""
    return {"status": "ok", "model": settings.gemini_model}

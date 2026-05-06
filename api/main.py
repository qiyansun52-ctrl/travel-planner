"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes.discover import router as discover_router
from app.routes.plan import router as plan_router

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


@app.get("/health")
async def health() -> dict:
    """Liveness check — used by Docker/load balancer."""
    return {"status": "ok", "model": settings.gemini_model}

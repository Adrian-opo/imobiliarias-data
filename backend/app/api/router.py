from fastapi import APIRouter

from app.api.routes import health, properties

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(properties.router, tags=["properties"])

# Additional routes can be added here
# api_router.include_router(sources.router, prefix="/sources", tags=["sources"])

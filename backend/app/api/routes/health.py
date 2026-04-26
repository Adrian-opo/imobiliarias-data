from fastapi import APIRouter

from app.schemas.property import HealthOut

router = APIRouter()


@router.get("/health", response_model=HealthOut)
def health_check():
    return HealthOut()

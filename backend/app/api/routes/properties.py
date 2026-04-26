from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.property import (
    PropertyFilterParams,
    PropertyOut,
    PropertyImageOut,
    PaginatedResponse,
    SourceOut,
    StatsOut,
    PropertyListOut,
    SourceSummaryOut,
)
from app.services.property_service import (
    get_properties,
    get_property_by_id,
    get_sources,
    get_stats,
)
from app.models.property import Property

router = APIRouter()


@router.get("/properties", response_model=PaginatedResponse)
def list_properties(
    business_type: Optional[str] = Query(None),
    property_type: Optional[str] = Query(None),
    purpose: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    neighborhood: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    min_area: Optional[float] = Query(None),
    bedrooms: Optional[int] = Query(None),
    garage_spaces: Optional[int] = Query(None),
    min_bedrooms: Optional[int] = Query(None),
    min_parking: Optional[int] = Query(None),
    is_new: Optional[bool] = Query(None),
    source_id: Optional[UUID] = Query(None),
    search: Optional[str] = Query(None),
    ordering: str = Query("last_seen_at"),
    sort: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    per_page: Optional[int] = Query(None, ge=1, le=100),
    db: Session = Depends(get_db),
):
    filters = PropertyFilterParams(
        business_type=business_type or purpose,
        property_type=property_type or type,
        neighborhood=neighborhood,
        min_price=min_price,
        max_price=max_price,
        min_area=min_area,
        bedrooms=bedrooms if bedrooms is not None else min_bedrooms,
        garage_spaces=garage_spaces if garage_spaces is not None else min_parking,
        is_new=is_new,
        source_id=source_id,
        search=search,
        # sort tem prioridade sobre ordering (era bug: `ordering or sort` ignorava sort)
        ordering=sort or ordering or "last_seen_at",
        page=page,
        page_size=page_size or per_page or 30,
    )
    effective_page_size = filters.page_size

    items, total = get_properties(db, filters)

    # Convert to list schema with thumbnail
    results = []
    for prop in items:
        thumbnail = None
        if prop.images:
            thumbnail = prop.images[0].url
        results.append(
            PropertyListOut(
                id=prop.id,
                source_id=prop.source_id,
                source_property_id=prop.source_property_id,
                source_url=prop.source_url,
                business_type=prop.business_type.value if hasattr(prop.business_type, 'value') else prop.business_type,
                property_type=prop.property_type.value if hasattr(prop.property_type, 'value') else prop.property_type,
                title=prop.title,
                price=float(prop.price) if prop.price else None,
                condominium_fee=float(prop.condominium_fee) if prop.condominium_fee else None,
                neighborhood=prop.neighborhood,
                bedrooms=prop.bedrooms,
                bathrooms=prop.bathrooms,
                garage_spaces=prop.garage_spaces,
                total_area=prop.total_area,
                built_area=prop.built_area,
                status=prop.status.value if hasattr(prop.status, 'value') else prop.status,
                is_new=prop.is_new,
                first_seen_at=prop.first_seen_at,
                last_seen_at=prop.last_seen_at,
                thumbnail_url=thumbnail,
                source=SourceSummaryOut.model_validate(prop.source) if prop.source else None,
            )
        )

    return PaginatedResponse(
        items=results,
        total=total,
        page=page,
        page_size=effective_page_size,
        total_pages=(total + effective_page_size - 1) // effective_page_size,
    )


@router.get("/properties/{property_id}", response_model=PropertyOut)
def get_property(property_id: UUID, db: Session = Depends(get_db)):
    prop = get_property_by_id(db, property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    # Build explicitly to avoid Pydantic from_attributes enum coercion issues
    return PropertyOut(
        id=prop.id,
        source_id=prop.source_id,
        source_property_id=prop.source_property_id,
        source_url=prop.source_url,
        business_type=prop.business_type.value if hasattr(prop.business_type, 'value') else prop.business_type,
        property_type=prop.property_type.value if hasattr(prop.property_type, 'value') else prop.property_type,
        title=prop.title,
        description=prop.description,
        price=float(prop.price) if prop.price is not None else None,
        condominium_fee=float(prop.condominium_fee) if prop.condominium_fee is not None else None,
        iptu=float(prop.iptu) if prop.iptu is not None else None,
        city=prop.city,
        state=prop.state,
        neighborhood=prop.neighborhood,
        address_text=prop.address_text,
        bedrooms=prop.bedrooms,
        suites=prop.suites,
        bathrooms=prop.bathrooms,
        garage_spaces=prop.garage_spaces,
        total_area=prop.total_area,
        built_area=prop.built_area,
        land_area=prop.land_area,
        status=prop.status.value if hasattr(prop.status, 'value') else prop.status,
        is_new=prop.is_new,
        published_at_source=prop.published_at_source,
        first_seen_at=prop.first_seen_at,
        last_seen_at=prop.last_seen_at,
        last_scraped_at=prop.last_scraped_at,
        created_at=prop.created_at,
        updated_at=prop.updated_at,
        images=[
            PropertyImageOut(
                id=img.id,
                url=img.url,
                position=img.position,
            )
            for img in (prop.images or [])
        ],
        source=SourceSummaryOut(
            id=prop.source.id,
            name=prop.source.name,
            base_url=prop.source.base_url,
            platform=prop.source.platform,
            is_active=prop.source.is_active,
        ) if prop.source else None,
    )


@router.get("/sources", response_model=list[SourceOut])
def list_sources(db: Session = Depends(get_db)):
    return get_sources(db)


@router.get("/stats", response_model=StatsOut)
def get_statistics(db: Session = Depends(get_db)):
    return get_stats(db)

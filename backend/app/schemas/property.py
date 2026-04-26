from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class PropertyImageOut(BaseModel):
    id: UUID
    url: str
    position: int

    model_config = {"from_attributes": True}


class SourceSummaryOut(BaseModel):
    id: UUID
    name: str
    base_url: str
    platform: str
    is_active: bool

    model_config = {"from_attributes": True}


class PropertyOut(BaseModel):
    id: UUID
    source_id: UUID
    source_property_id: str
    source_url: str
    business_type: str
    property_type: str
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    condominium_fee: Optional[float] = None
    iptu: Optional[float] = None
    city: str
    state: str
    neighborhood: Optional[str] = None
    address_text: Optional[str] = None
    bedrooms: Optional[int] = None
    suites: Optional[int] = None
    bathrooms: Optional[int] = None
    garage_spaces: Optional[int] = None
    total_area: Optional[float] = None
    built_area: Optional[float] = None
    land_area: Optional[float] = None
    status: str
    is_new: bool
    published_at_source: Optional[datetime] = None
    first_seen_at: datetime
    last_seen_at: datetime
    last_scraped_at: datetime
    created_at: datetime
    updated_at: datetime
    images: list[PropertyImageOut] = []
    source: Optional[SourceSummaryOut] = None
    model_config = {"from_attributes": True}


class PropertyListOut(BaseModel):
    id: UUID
    source_id: UUID
    source_property_id: str
    source_url: str
    business_type: str
    property_type: str
    title: Optional[str] = None
    price: Optional[float] = None
    condominium_fee: Optional[float] = None
    neighborhood: Optional[str] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    garage_spaces: Optional[int] = None
    total_area: Optional[float] = None
    built_area: Optional[float] = None
    status: str
    is_new: bool
    first_seen_at: datetime
    last_seen_at: datetime
    thumbnail_url: Optional[str] = None
    source: Optional[SourceSummaryOut] = None

    model_config = {"from_attributes": True}


class PropertyFilterParams(BaseModel):
    business_type: Optional[str] = None
    property_type: Optional[str] = None
    neighborhood: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_area: Optional[float] = None
    bedrooms: Optional[int] = None
    garage_spaces: Optional[int] = None
    is_new: Optional[bool] = None
    source_id: Optional[UUID] = None
    search: Optional[str] = None
    ordering: Optional[str] = "last_seen_at"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=30, ge=1, le=100)


class PaginatedResponse(BaseModel):
    items: list[PropertyListOut]
    total: int
    page: int
    page_size: int
    total_pages: int


class SourceOut(BaseModel):
    id: UUID
    name: str
    base_url: str
    platform: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class StatsOut(BaseModel):
    total_properties: int
    total_sources: int
    by_type: dict[str, int]
    by_neighborhood: dict[str, int]
    by_business_type: dict[str, int]
    new_last_24h: int
    new_last_3d: int
    new_last_7_days: int
    updated_at: str


class HealthOut(BaseModel):
    status: str = "ok"
    service: str = "imobiliarias-data"
    version: str = "0.1.0"

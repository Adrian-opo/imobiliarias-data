import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String, Integer, Float, Boolean, DateTime, Text, Numeric,
    ForeignKey, func, Enum as SAEnum, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

from app.database import Base


class BusinessType(str, enum.Enum):
    """Sale or rent."""
    SALE = "sale"
    RENT = "rent"


class PropertyType(str, enum.Enum):
    """Property category."""
    CASA = "casa"
    APARTAMENTO = "apartamento"
    TERRENO = "terreno"
    SOBRADO = "sobrado"
    COMERCIAL = "comercial"
    SALA = "sala"
    BARRACAO = "barracao"
    CHACARA = "chacara"
    SITIO = "sitio"
    FAZENDA = "fazenda"
    OUTRO = "outro"


class PropertyStatus(str, enum.Enum):
    """Current visibility status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    REMOVED = "removed"


class Property(Base):
    __tablename__ = "properties"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id"), nullable=False
    )
    source_property_id: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="ID from source portal"
    )
    source_url: Mapped[str] = mapped_column(String(1024), nullable=False)

    business_type: Mapped[BusinessType] = mapped_column(
        SAEnum(BusinessType, create_constraint=False, validate_strings=True, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    property_type: Mapped[PropertyType] = mapped_column(
        SAEnum(PropertyType, create_constraint=False, validate_strings=True, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )

    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    price: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    condominium_fee: Mapped[Optional[float]] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    iptu: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)

    city: Mapped[str] = mapped_column(String(100), default="Ji-Paraná", nullable=False)
    state: Mapped[str] = mapped_column(String(2), default="RO", nullable=False)
    neighborhood: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    address_text: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    bedrooms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    suites: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bathrooms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    garage_spaces: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    total_area: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    built_area: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    land_area: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    status: Mapped[PropertyStatus] = mapped_column(
        SAEnum(PropertyStatus, create_constraint=False, validate_strings=True, values_callable=lambda x: [e.value for e in x]),
        default=PropertyStatus.ACTIVE, nullable=False,
    )
    is_new: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    published_at_source: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    source = relationship("Source", back_populates="properties")
    images = relationship(
        "PropertyImage", back_populates="property", cascade="all, delete-orphan",
        order_by="PropertyImage.position"
    )
    raw_snapshots = relationship(
        "PropertyRaw", back_populates="property", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_property_source_ref", "source_id", "source_property_id", unique=True),
        Index("idx_property_status", "status"),
        Index("idx_property_neighborhood", "neighborhood"),
        Index("idx_property_business_type", "business_type"),
    )

    def __repr__(self):
        return f"<Property {self.title} [{self.business_type.value}]>"

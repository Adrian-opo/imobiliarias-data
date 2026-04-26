"""
Business logic for property CRUD and deduplication.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.property import Property, PropertyStatus, BusinessType, PropertyType
from app.models.property_image import PropertyImage
from app.models.property_raw import PropertyRaw
from app.models.source import Source
from app.schemas.property import PropertyFilterParams, PropertyListOut


def _enum_to_str(value) -> Optional[str]:
    """Safely convert a Python enum or other value to string."""
    if value is None:
        return None
    if hasattr(value, 'value'):
        return str(value.value)
    if isinstance(value, str):
        return value
    return str(value)


def get_properties(
    db: Session,
    filters: PropertyFilterParams,
) -> tuple[list[Property], int]:
    """
    Query properties with filters, sorting, and pagination.
    Returns (items, total_count).
    """
    query = db.query(Property).filter(Property.status == PropertyStatus.ACTIVE)

    # Apply filters — validate enum values to prevent SQLAlchemy ValueError
    if filters.business_type:
        try:
            BusinessType(filters.business_type)
            query = query.filter(Property.business_type == filters.business_type)
        except ValueError:
            pass  # Invalid enum value, skip filter silently
    if filters.property_type:
        try:
            PropertyType(filters.property_type)
            query = query.filter(Property.property_type == filters.property_type)
        except ValueError:
            pass  # Invalid enum value, skip filter silently
    if filters.neighborhood:
        query = query.filter(
            func.lower(Property.neighborhood) == filters.neighborhood.lower()
        )
    if filters.min_price is not None:
        query = query.filter(Property.price >= filters.min_price)
    if filters.max_price is not None:
        query = query.filter(Property.price <= filters.max_price)
    if filters.min_area is not None:
        query = query.filter(
            or_(
                Property.total_area >= filters.min_area,
                Property.built_area >= filters.min_area,
            )
        )
    if filters.bedrooms is not None:
        query = query.filter(Property.bedrooms >= filters.bedrooms)
    if filters.garage_spaces is not None:
        query = query.filter(Property.garage_spaces >= filters.garage_spaces)
    if filters.is_new is not None:
        query = query.filter(Property.is_new == filters.is_new)
    if filters.source_id:
        query = query.filter(Property.source_id == filters.source_id)
    if filters.search:
        search_term = f"%{filters.search}%"
        query = query.filter(
            or_(
                Property.title.ilike(search_term),
                Property.description.ilike(search_term),
                Property.neighborhood.ilike(search_term),
                Property.address_text.ilike(search_term),
            )
        )

    # Count total before pagination
    total = query.count()

    # Apply ordering
    ordering_map = {
        "price_asc": Property.price.asc(),
        "price_desc": Property.price.desc(),
        "date_asc": Property.last_seen_at.asc(),
        "date_desc": Property.last_seen_at.desc(),
        "area_asc": Property.total_area.asc(),
        "area_desc": Property.total_area.desc(),
        "newest": Property.first_seen_at.desc(),
        "last_seen_at": Property.last_seen_at.desc(),
    }
    order_col = ordering_map.get(filters.ordering, Property.last_seen_at.desc())
    query = query.order_by(order_col)

    # Pagination
    offset = (filters.page - 1) * filters.page_size
    items = query.offset(offset).limit(filters.page_size).all()

    return items, total


def get_property_by_id(db: Session, property_id: UUID) -> Optional[Property]:
    return db.query(Property).filter(Property.id == property_id).first()


def get_sources(db: Session) -> list[Source]:
    return db.query(Source).order_by(Source.name).all()


def get_stats(db: Session) -> dict:
    """Compute aggregate statistics."""
    total = db.query(func.count(Property.id)).filter(
        Property.status == PropertyStatus.ACTIVE
    ).scalar() or 0
    total_sources = db.query(func.count(Source.id)).filter(Source.is_active.is_(True)).scalar() or 0

    # By property type
    by_type_rows = (
        db.query(Property.property_type, func.count(Property.id))
        .filter(Property.status == PropertyStatus.ACTIVE)
        .group_by(Property.property_type)
        .all()
    )
    by_type: dict[str, int] = {}
    for row in by_type_rows:
        key = _enum_to_str(row[0])
        if key is not None:
            by_type[key] = row[1]

    # By neighborhood
    by_neighborhood_rows = (
        db.query(Property.neighborhood, func.count(Property.id))
        .filter(
            Property.status == PropertyStatus.ACTIVE,
            Property.neighborhood.isnot(None),
        )
        .group_by(Property.neighborhood)
        .order_by(func.count(Property.id).desc())
        .limit(20)
        .all()
    )
    by_neighborhood = {row[0]: row[1] for row in by_neighborhood_rows if row[0]}

    # By business type
    by_business_rows = (
        db.query(Property.business_type, func.count(Property.id))
        .filter(Property.status == PropertyStatus.ACTIVE)
        .group_by(Property.business_type)
        .all()
    )
    by_business_type: dict[str, int] = {}
    for row in by_business_rows:
        key = _enum_to_str(row[0])
        if key is not None:
            by_business_type[key] = row[1]

    # New in last 7 days
    one_day_ago = datetime.now(timezone.utc) - timedelta(days=1)
    three_days_ago = datetime.now(timezone.utc) - timedelta(days=3)
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    new_last_24h = (
        db.query(func.count(Property.id))
        .filter(
            Property.status == PropertyStatus.ACTIVE,
            Property.first_seen_at >= one_day_ago,
        )
        .scalar()
    ) or 0
    new_last_3 = (
        db.query(func.count(Property.id))
        .filter(
            Property.status == PropertyStatus.ACTIVE,
            Property.first_seen_at >= three_days_ago,
        )
        .scalar()
    ) or 0
    new_last_7 = (
        db.query(func.count(Property.id))
        .filter(
            Property.status == PropertyStatus.ACTIVE,
            Property.first_seen_at >= seven_days_ago,
        )
        .scalar()
    ) or 0

    return {
        "total_properties": total,
        "total_sources": total_sources,
        "by_type": by_type,
        "by_neighborhood": by_neighborhood,
        "by_business_type": by_business_type,
        "new_last_24h": new_last_24h,
        "new_last_3d": new_last_3,
        "new_last_7_days": new_last_7,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def upsert_property(
    db: Session,
    source_id: UUID,
    source_property_id: str,
    source_url: str,
    business_type: str,
    property_type: str,
    content_hash: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    price: Optional[float] = None,
    condominium_fee: Optional[float] = None,
    iptu: Optional[float] = None,
    neighborhood: Optional[str] = None,
    address_text: Optional[str] = None,
    bedrooms: Optional[int] = None,
    suites: Optional[int] = None,
    bathrooms: Optional[int] = None,
    garage_spaces: Optional[int] = None,
    total_area: Optional[float] = None,
    built_area: Optional[float] = None,
    land_area: Optional[float] = None,
    published_at_source: Optional[datetime] = None,
    images: Optional[list[dict]] = None,
) -> tuple[Property, bool]:
    """
    Create or update a property based on identity key (source_id, source_property_id).
    Returns (property, is_new).
    """
    now = datetime.now(timezone.utc)
    existing = (
        db.query(Property)
        .filter(
            Property.source_id == source_id,
            Property.source_property_id == source_property_id,
        )
        .first()
    )

    if existing:
        # Update
        is_new = False
        was_removed = existing.status == PropertyStatus.REMOVED

        existing.source_url = source_url
        existing.business_type = business_type
        existing.property_type = property_type
        existing.title = title
        existing.description = description
        existing.price = price
        existing.condominium_fee = condominium_fee
        existing.iptu = iptu
        existing.neighborhood = neighborhood
        existing.address_text = address_text
        existing.bedrooms = bedrooms
        existing.suites = suites
        existing.bathrooms = bathrooms
        existing.garage_spaces = garage_spaces
        existing.total_area = total_area
        existing.built_area = built_area
        existing.land_area = land_area
        existing.last_seen_at = now
        existing.last_scraped_at = now

        # If was removed and reappeared, reactivate
        if was_removed:
            existing.status = PropertyStatus.ACTIVE
            # Keep original first_seen_at

        # Update is_new based on first_seen_at
        existing.is_new = (now - existing.first_seen_at) < timedelta(days=7)

        # Update images if provided
        if images is not None:
            _sync_images(db, existing, images)

        db.flush()
        return existing, False
    else:
        # Create new
        prop = Property(
            source_id=source_id,
            source_property_id=source_property_id,
            source_url=source_url,
            business_type=business_type,
            property_type=property_type,
            title=title,
            description=description,
            price=price,
            condominium_fee=condominium_fee,
            iptu=iptu,
            neighborhood=neighborhood,
            address_text=address_text,
            bedrooms=bedrooms,
            suites=suites,
            bathrooms=bathrooms,
            garage_spaces=garage_spaces,
            total_area=total_area,
            built_area=built_area,
            land_area=land_area,
            published_at_source=published_at_source,
            first_seen_at=now,
            last_seen_at=now,
            last_scraped_at=now,
            content_hash=content_hash,
            is_new=True,
            status=PropertyStatus.ACTIVE,
        )
        db.add(prop)
        db.flush()

        if images:
            _sync_images(db, prop, images)

        return prop, True


def _sync_images(db: Session, property: Property, images_data: list[dict]):
    """Sync images for a property: delete old, add new."""
    # Delete existing
    db.query(PropertyImage).filter(
        PropertyImage.property_id == property.id
    ).delete()

    # Add new
    for img_data in images_data:
        img = PropertyImage(
            property_id=property.id,
            url=img_data["url"],
            position=img_data.get("position", 0),
        )
        db.add(img)


def mark_removed_properties(db: Session, source_id: UUID, active_ids: set[str]):
    """
    Mark as 'removed' properties from a source that were not found in the latest scrape.
    A property is removed if it hasn't been seen for 3 scrape cycles (~3 days).
    """
    now = datetime.now(timezone.utc)
    three_days_ago = now - timedelta(days=3)

    removed = (
        db.query(Property)
        .filter(
            Property.source_id == source_id,
            Property.status == PropertyStatus.ACTIVE,
            Property.source_property_id.notin_(active_ids),
            Property.last_seen_at < three_days_ago,
        )
        .update({"status": PropertyStatus.REMOVED, "is_new": False})
    )
    return removed

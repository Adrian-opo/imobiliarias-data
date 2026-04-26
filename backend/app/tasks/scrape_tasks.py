"""
Celery tasks for scraping real estate portals.

Each task:
1. Instantiates the appropriate scraper
2. Runs scrape_listings() to get property URLs
3. For each listing, runs scrape_detail() + normalize()
4. Upserts into the database via property_service
5. Marks removed properties
6. Logs everything in a ScrapeRun record
7. Marks status as success/partial/failed with error details
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from celery import shared_task
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.source import Source
from app.models.scrape_run import ScrapeRun, ScrapeRunStatus
from app.models.property_raw import PropertyRaw
from app.scrapers.registry import get_scraper, get_all_scrapers
from app.scrapers.base import BaseScraper
from app.services.property_service import upsert_property, mark_removed_properties

logger = logging.getLogger(__name__)


def _run_async(coro) -> Optional[any]:
    """Run an async coroutine in a sync context using a dedicated event loop."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _get_scraper_for_source(source: Source) -> Optional[type[BaseScraper]]:
    """Resolve the scraper class for a given source by name matching."""
    # Direct match with underscored name
    name_key = source.name.lower().replace(" ", "_")
    cls = get_scraper(name_key)
    if cls:
        return cls

    # Try first word
    first_word = source.name.split()[0].lower()
    cls = get_scraper(first_word)
    if cls:
        return cls

    # Try platform name
    cls = get_scraper(source.platform.lower())
    if cls:
        return cls

    # Full registry scan
    all_scrapers = get_all_scrapers()
    for key, scraper_cls in all_scrapers.items():
        if hasattr(scraper_cls, 'source_name') and source.name.lower() in scraper_cls.source_name.lower():
            return scraper_cls
        if hasattr(scraper_cls, 'platform') and source.platform.lower() == scraper_cls.platform.lower():
            return scraper_cls

    return None


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def run_scrape(self, source_id: str):
    """
    Execute a full scrape cycle for a single source.

    Handles the full pipeline:
    - Fetches listings
    - Scrapes detail for each
    - Normalizes and persists
    - Tracks stats in ScrapeRun
    - Marks removed properties
    """
    source_uuid = UUID(source_id)
    db: Session = SessionLocal()

    try:
        # --- Source lookup ---
        source = db.query(Source).filter(Source.id == source_uuid).first()
        if not source:
            logger.error("[Scrape] Source not found: %s", source_id)
            return {"error": "Source not found"}

        if not source.is_active:
            logger.info("[Scrape] Source '%s' is inactive, skipping", source.name)
            return {"status": "skipped", "reason": "inactive"}

        logger.info("[Scrape] Starting scrape for '%s' (%s)", source.name, source.platform)

        # --- Create scrape run log ---
        run = ScrapeRun(
            source_id=source_uuid,
            started_at=datetime.now(timezone.utc),
            status=ScrapeRunStatus.RUNNING,
        )
        db.add(run)
        db.commit()

        # --- Resolve scraper ---
        scraper_cls = _get_scraper_for_source(source)
        if not scraper_cls:
            logger.error("[Scrape] No scraper registered for '%s' (platform=%s)",
                         source.name, source.platform)
            run.status = ScrapeRunStatus.FAILED
            run.error_log = {"error": f"No scraper for {source.name} (platform={source.platform})"}
            run.finished_at = datetime.now(timezone.utc)
            db.commit()
            return {"error": f"No scraper for {source.name}"}

        scraper = scraper_cls(source_uuid, source.base_url)
        logger.info("[Scrape] Using scraper: %s", scraper_cls.__name__)

        # --- Step 1: scrape listings with pagination rotation ---
        try:
            # Count successful runs to use as page offset (rotation across cycles)
            prev_runs = db.query(ScrapeRun).filter(
                ScrapeRun.source_id == source_uuid,
                ScrapeRun.status == ScrapeRunStatus.SUCCESS,
            ).count()
            page_offset = prev_runs  # each successful run advances the page window
            listings = _run_async(scraper.scrape_listings(page_offset=page_offset))
            if not listings:
                listings = []
            logger.info("[Scrape] '%s': found %d listings", source.name, len(listings))
        except Exception as e:
            logger.error("[Scrape] '%s': listing fetch failed: %s", source.name, e)
            run.status = ScrapeRunStatus.FAILED
            run.error_log = {"error": f"Listing fetch failed: {str(e)}"}
            run.finished_at = datetime.now(timezone.utc)
            db.commit()
            return {"error": f"Listing failed: {str(e)}", "source": source.name}

        # --- Step 2: scrape details and upsert ---
        properties_found = len(listings)
        properties_new = 0
        properties_updated = 0
        properties_skipped = 0
        errors = []
        active_ids = set()

        for idx, listing in enumerate(listings):
            prop_id = listing.get("source_property_id", "")
            url = listing.get("url", "")

            if not prop_id or not url:
                errors.append({"listing": idx, "error": "Missing source_property_id or url"})
                continue

            try:
                # Pass through extra kwargs from listing (e.g., business_type_hint)
                detail_kwargs = {k: v for k, v in listing.items() if k not in ("source_property_id", "url")}
                raw_data = _run_async(scraper.scrape_detail(prop_id, url, **detail_kwargs))

                if not raw_data:
                    logger.debug("[Scrape] '%s': no data for %s", source.name, prop_id)
                    continue

                # Normalize
                normalized = scraper.normalize(raw_data)
                if not normalized:
                    logger.debug("[Scrape] '%s': normalize failed for %s", source.name, prop_id)
                    properties_skipped += 1
                    continue

                # Save raw snapshot
                raw_record = PropertyRaw(
                    source_id=source_uuid,
                    raw_json=raw_data,
                )
                db.add(raw_record)
                db.flush()

                # Upsert normalized property
                prop, is_new = upsert_property(
                    db,
                    source_id=source_uuid,
                    source_property_id=normalized["source_property_id"],
                    source_url=normalized["source_url"],
                    business_type=normalized["business_type"],
                    property_type=normalized["property_type"],
                    content_hash=normalized.get("content_hash", ""),
                    title=normalized.get("title"),
                    description=normalized.get("description"),
                    price=normalized.get("price"),
                    condominium_fee=normalized.get("condominium_fee"),
                    iptu=normalized.get("iptu"),
                    neighborhood=normalized.get("neighborhood"),
                    address_text=normalized.get("address_text"),
                    bedrooms=normalized.get("bedrooms"),
                    suites=normalized.get("suites"),
                    bathrooms=normalized.get("bathrooms"),
                    garage_spaces=normalized.get("garage_spaces"),
                    total_area=normalized.get("total_area"),
                    built_area=normalized.get("built_area"),
                    land_area=normalized.get("land_area"),
                    published_at_source=normalized.get("published_at_source"),
                    images=normalized.get("images"),
                )

                # Link raw snapshot to the property
                raw_record.property_id = prop.id

                if is_new:
                    properties_new += 1
                else:
                    properties_updated += 1

                active_ids.add(prop_id)

            except Exception as e:
                logger.error("[Scrape] '%s': error processing %s: %s", source.name, url, e)
                errors.append({"url": url, "error": str(e)})
                continue

        # --- Step 3: mark removed properties ---
        try:
            removed_count = mark_removed_properties(db, source_uuid, active_ids)
            if removed_count:
                logger.info("[Scrape] '%s': marked %d properties as removed",
                            source.name, removed_count)
        except Exception as e:
            logger.error("[Scrape] '%s': error marking removed: %s", source.name, e)

        # --- Step 4: finalize scrape run ---
        has_errors = len(errors) > 0
        has_data = properties_new + properties_updated > 0

        if has_errors and has_data:
            final_status = ScrapeRunStatus.PARTIAL
        elif has_errors and not has_data:
            final_status = ScrapeRunStatus.FAILED
        else:
            final_status = ScrapeRunStatus.SUCCESS

        run.status = final_status
        run.finished_at = datetime.now(timezone.utc)
        run.properties_found = properties_found
        run.properties_new = properties_new
        run.properties_updated = properties_updated
        if errors:
            run.error_log = {"errors": errors[:50]}  # cap at 50

        db.commit()

        logger.info(
            "[Scrape] '%s' done: found=%d new=%d updated=%d skipped=%d errors=%d status=%s",
            source.name, properties_found, properties_new, properties_updated,
            properties_skipped, len(errors), final_status.value,
        )

        return {
            "source": source.name,
            "platform": source.platform,
            "found": properties_found,
            "new": properties_new,
            "updated": properties_updated,
            "skipped": properties_skipped,
            "errors": len(errors),
            "status": final_status.value,
        }

    except Exception as e:
        logger.error("[Scrape] Critical failure for %s: %s", source_id, e)
        try:
            db.rollback()
            # Try to update scrape run status if exists
            run = db.query(ScrapeRun).filter(
                ScrapeRun.source_id == source_uuid,
                ScrapeRun.status == ScrapeRunStatus.RUNNING,
            ).order_by(ScrapeRun.started_at.desc()).first()
            if run:
                run.status = ScrapeRunStatus.FAILED
                run.finished_at = datetime.now(timezone.utc)
                run.error_log = {"critical_error": str(e)}
                db.commit()
        except Exception:
            db.rollback()
        raise self.retry(exc=e)

    finally:
        db.close()


@shared_task
def run_all_scrapes():
    """
    Run scrapes for all active sources.
    Dispatched by Celery Beat at scheduled intervals (12:00 and 18:00 UTC).
    """
    db: Session = SessionLocal()
    try:
        sources = db.query(Source).filter(Source.is_active.is_(True)).all()
        logger.info("[ScrapeCycle] Starting cycle for %d sources", len(sources))

        results = []
        for source in sources:
            try:
                result = run_scrape.delay(str(source.id))
                results.append({"source": source.name, "task_id": result.id})
                logger.info("[ScrapeCycle] Dispatched: %s (task=%s)", source.name, result.id)
            except Exception as e:
                logger.error("[ScrapeCycle] Failed to dispatch '%s': %s", source.name, e)
                results.append({"source": source.name, "error": str(e)})

        logger.info("[ScrapeCycle] Dispatched %d/%d tasks", len(results), len(sources))
        return {"dispatched": len(results), "sources": len(sources), "results": results}

    finally:
        db.close()

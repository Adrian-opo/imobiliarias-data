"""
Tests for deduplication and content_hash logic.

These test the business rules for:
- Identity key: (source_id, source_property_id)
- Content hash change detection
- is_new = first_seen_at < 7 days
- Removed property reactivation
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.services.normalize import compute_content_hash


class TestContentHashDedup:
    """Content hash should detect meaningful changes."""

    def test_price_change_detected(self):
        h1 = compute_content_hash(100000.0, "Casa", "teste", "Centro", 2, 1, 1, 100.0)
        h2 = compute_content_hash(150000.0, "Casa", "teste", "Centro", 2, 1, 1, 100.0)
        assert h1 != h2, "Price change must produce different hash"

    def test_bedroom_change_detected(self):
        h1 = compute_content_hash(100000.0, "Casa", "teste", "Centro", 2, 1, 1, 100.0)
        h2 = compute_content_hash(100000.0, "Casa", "teste", "Centro", 3, 1, 1, 100.0)
        assert h1 != h2, "Bedroom change must produce different hash"

    def same_fields_produce_same_hash(self):
        fields = (200000.0, "Title", "Desc", "Bairro", 3, 2, 2, 150.0)
        h1 = compute_content_hash(*fields)
        h2 = compute_content_hash(*fields)
        assert h1 == h2, "Same fields must produce identical hash"


class TestPropertyUpsertLogic:
    """Test the upsert_property business logic rules."""

    def test_identity_key_uniqueness(self):
        """
        Identity key = (source_id, source_property_id).
        Two properties with same key should update, not create.
        """
        source_id = uuid4()
        source_property_id = "prop-123"

        # Mock the DB query that looks for existing property
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        from app.services.property_service import upsert_property

        # First call -> create (existing is None)
        prop1, is_new1 = upsert_property(
            db=mock_db,
            source_id=source_id,
            source_property_id=source_property_id,
            source_url="http://example.com/1",
            business_type="sale",
            property_type="casa",
            content_hash="abc123",
            title="Casa",
            price=100000.0,
        )
        # We can't easily test the return without a real DB,
        # but we can verify the query was made correctly
        mock_db.add.assert_called()
        mock_db.reset_mock()

        # Now simulate existing property
        mock_prop = MagicMock()
        mock_prop.source_id = source_id
        mock_prop.source_property_id = source_property_id
        mock_prop.status = "active"  # use string for simplicity
        mock_prop.first_seen_at = datetime.now(timezone.utc) - timedelta(days=1)
        mock_prop.is_new = True
        mock_db.query.return_value.filter.return_value.first.return_value = mock_prop

        prop2, is_new2 = upsert_property(
            db=mock_db,
            source_id=source_id,
            source_property_id=source_property_id,
            source_url="http://example.com/2",
            business_type="sale",
            property_type="casa",
            content_hash="def456",
            title="Casa Atualizada",
            price=120000.0,
        )
        assert is_new2 is False

    def test_removed_property_reactivation(self):
        """
        If a property was 'removed' and reappears, reactivate it
        while keeping original first_seen_at.
        """
        source_id = uuid4()
        source_property_id = "prop-456"
        original_first_seen = datetime.now(timezone.utc) - timedelta(days=30)

        mock_db = MagicMock()
        mock_prop = MagicMock()
        mock_prop.source_id = source_id
        mock_prop.source_property_id = source_property_id
        mock_prop.status = "removed"
        mock_prop.first_seen_at = original_first_seen
        mock_prop.is_new = False
        mock_db.query.return_value.filter.return_value.first.return_value = mock_prop

        from app.services.property_service import upsert_property

        prop, is_new = upsert_property(
            db=mock_db,
            source_id=source_id,
            source_property_id=source_property_id,
            source_url="http://example.com/3",
            business_type="sale",
            property_type="casa",
            content_hash="xyz789",
        )
        # Should be reactivated (status set to active) and not new
        assert is_new is False
        # first_seen_at should be preserved (not updated)
        assert prop.first_seen_at == original_first_seen

    def test_new_property_is_new_flag(self):
        """
        A newly created property should have is_new=True.
        """
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        from app.services.property_service import upsert_property

        prop, is_new = upsert_property(
            db=mock_db,
            source_id=uuid4(),
            source_property_id="prop-789",
            source_url="http://example.com/4",
            business_type="rent",
            property_type="apartamento",
            content_hash="aaa",
        )
        assert is_new is True

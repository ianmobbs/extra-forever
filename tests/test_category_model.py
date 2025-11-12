"""
Tests for Category model.
"""

import pytest
from sqlalchemy.exc import IntegrityError

from models import Category


class TestCategoryModel:
    """Test Category ORM model."""

    def test_create_category(self, db_session):
        """Test creating a Category instance."""
        category = Category(
            name="Work Travel", description="Work-related travel receipts from airlines"
        )
        db_session.add(category)
        db_session.commit()

        assert category.id is not None
        assert category.name == "Work Travel"
        assert category.description == "Work-related travel receipts from airlines"

    def test_category_repr(self, db_session):
        """Test Category __repr__ method."""
        category = Category(name="Test Category", description="Short description")
        db_session.add(category)
        db_session.commit()

        repr_str = repr(category)
        assert "Test Category" in repr_str
        assert "Short description" in repr_str

    def test_category_repr_truncates_long_description(self, db_session):
        """Test Category __repr__ truncates long descriptions."""
        long_desc = "A" * 200
        category = Category(name="Test", description=long_desc)
        db_session.add(category)
        db_session.commit()

        repr_str = repr(category)
        assert "..." in repr_str
        assert len(repr_str) < len(long_desc)

    def test_category_unique_name_constraint(self, db_session):
        """Test that category names must be unique."""
        cat1 = Category(name="Unique", description="First")
        db_session.add(cat1)
        db_session.commit()

        cat2 = Category(name="Unique", description="Second")
        db_session.add(cat2)

        with pytest.raises(IntegrityError):
            db_session.commit()

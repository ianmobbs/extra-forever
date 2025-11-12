"""
Tests for app/stores/sqlite_store.py
"""

from contextlib import suppress

from sqlalchemy.orm import Session

from app.stores.sqlite_store import SQLiteStore
from models import Message


class TestSQLiteStore:
    """Test SQLiteStore class."""

    def test_store_initialization(self, temp_db):
        """Test store can be initialized."""
        store = SQLiteStore(db_path=temp_db, echo=False)
        assert store.db_path == temp_db
        assert store.engine is not None

    def test_init_db_creates_tables(self, temp_db):
        """Test init_db creates database tables."""
        store = SQLiteStore(db_path=temp_db, echo=False)
        store.init_db(drop_existing=False)

        # Verify tables exist
        from sqlalchemy import inspect

        inspector = inspect(store.engine)
        tables = inspector.get_table_names()
        assert "messages" in tables

    def test_init_db_drops_existing(self, temp_db, sample_message):
        """Test init_db can drop existing tables."""
        store = SQLiteStore(db_path=temp_db, echo=False)
        store.init_db(drop_existing=False)

        # Add a message
        session = store.create_session()
        session.add(sample_message)
        session.commit()

        count = session.query(Message).count()
        assert count == 1
        session.close()

        # Drop and recreate
        store.init_db(drop_existing=True)

        # Verify data is gone
        session = store.create_session()
        count = session.query(Message).count()
        assert count == 0
        session.close()

    def test_create_session(self, sqlite_store):
        """Test create_session returns a valid session."""
        session = sqlite_store.create_session()
        assert isinstance(session, Session)
        session.close()

    def test_get_session_generator(self, sqlite_store):
        """Test get_session generator."""
        gen = sqlite_store.get_session()
        session = next(gen)
        assert isinstance(session, Session)

        # Generator should close session automatically
        with suppress(StopIteration):
            next(gen)

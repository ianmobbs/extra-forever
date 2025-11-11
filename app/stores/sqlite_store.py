"""
SQLite store for database session management and initialization.
"""
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from models import Base


class SQLiteStore:
    """Handles SQLite database connection and session management."""
    
    def __init__(self, db_path: str = "sqlite:///messages.db", echo: bool = False):
        self.db_path = db_path
        self.engine = create_engine(db_path, echo=echo)
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def init_db(self, drop_existing: bool = False) -> None:
        """Initialize database tables."""
        if drop_existing:
            Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
    
    def get_session(self) -> Generator[Session, None, None]:
        """Get a database session with automatic cleanup."""
        session = self.SessionLocal()
        try:
            yield session
        finally:
            session.close()
    
    def create_session(self) -> Session:
        """Create a new database session (caller must close)."""
        return self.SessionLocal()


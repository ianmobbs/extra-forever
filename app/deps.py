"""
FastAPI dependencies for dependency injection.

This module provides shared dependencies for the FastAPI app, including
database sessions and service instances.
"""

from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.config import config
from app.services.bootstrap_service import BootstrapService
from app.services.categories_service import CategoriesService
from app.services.classification import ClassificationService
from app.services.messages_service import MessagesService
from app.stores.sqlite_store import SQLiteStore

# Shared store instance (initialized lazily)
_store: SQLiteStore | None = None


def get_store() -> SQLiteStore:
    """
    Get or create the shared SQLiteStore instance.

    Returns:
        Shared SQLiteStore instance
    """
    global _store
    if _store is None:
        _store = SQLiteStore(db_path=config.DATABASE_URL, echo=config.DATABASE_ECHO)
        # Initialize database tables (without dropping)
        _store.init_db(drop_existing=False)
    return _store


def get_db_session(store: SQLiteStore = Depends(get_store)) -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a database session.

    Usage:
        @app.get("/endpoint")
        def endpoint(db: Session = Depends(get_db_session)):
            # use db session

    Args:
        store: SQLiteStore instance (injected)

    Yields:
        Database session
    """
    session = store.create_session()
    try:
        yield session
    finally:
        session.close()


def get_classification_service(
    db_session: Session = Depends(get_db_session),
) -> ClassificationService:
    """
    FastAPI dependency that provides a ClassificationService instance.

    Args:
        db_session: Database session (injected)

    Returns:
        ClassificationService instance
    """
    return ClassificationService(
        db_session, top_n=config.CLASSIFICATION_TOP_N, threshold=config.CLASSIFICATION_THRESHOLD
    )


def get_categories_service(db_session: Session = Depends(get_db_session)) -> CategoriesService:
    """
    FastAPI dependency that provides a CategoriesService instance.

    Args:
        db_session: Database session (injected)

    Returns:
        CategoriesService instance
    """
    return CategoriesService(db_session)


def get_messages_service(
    db_session: Session = Depends(get_db_session),
    store: SQLiteStore = Depends(get_store),
    classification_service: ClassificationService = Depends(get_classification_service),
) -> MessagesService:
    """
    FastAPI dependency that provides a MessagesService instance.

    Args:
        db_session: Database session (injected)
        store: SQLiteStore (injected, needed for import operations)
        classification_service: ClassificationService (injected, needed for auto-classification)

    Returns:
        MessagesService instance
    """
    return MessagesService(db_session, classification_service=classification_service, store=store)


def get_bootstrap_service(
    store: SQLiteStore = Depends(get_store),
    messages_service: MessagesService = Depends(get_messages_service),
    categories_service: CategoriesService = Depends(get_categories_service),
) -> BootstrapService:
    """
    FastAPI dependency that provides a BootstrapService instance.

    Args:
        store: SQLiteStore instance (injected)
        messages_service: MessagesService instance (injected)
        categories_service: CategoriesService instance (injected)

    Returns:
        BootstrapService instance
    """
    return BootstrapService(store, messages_service, categories_service)

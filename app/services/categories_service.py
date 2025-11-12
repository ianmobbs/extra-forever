"""
Categories service for orchestrating category operations.
"""

from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.managers.category_manager import CategoryManager
from app.services.embedding_service import EmbeddingService
from models import Category


@dataclass
class CategoryResult:
    """Result of a category operation."""

    category: Category


class CategoriesService:
    """Service for orchestrating category operations."""

    def __init__(self, db_session: Session, embedding_service: EmbeddingService | None = None):
        self.db_session = db_session
        self.embedding_service = embedding_service or EmbeddingService()

    def create_category(self, name: str, description: str) -> CategoryResult:
        """
        Create a new category.

        Args:
            name: Category name
            description: Natural-language description of the category

        Returns:
            CategoryResult with the created category
        """
        # Create temporary category object for embedding
        temp_category = Category(name=name, description=description)

        # Generate embedding
        embedding = self.embedding_service.embed_category(temp_category)

        manager = CategoryManager(self.db_session)
        try:
            category = manager.create(name=name, description=description, embedding=embedding)
            self.db_session.commit()
            self.db_session.refresh(category)
            return CategoryResult(category=category)
        except IntegrityError as e:
            self.db_session.rollback()
            raise ValueError(f"Category with name '{name}' already exists") from e
        except Exception:
            self.db_session.rollback()
            raise

    def get_category(self, category_id: int) -> CategoryResult | None:
        """
        Get a category by ID.

        Args:
            category_id: Category ID

        Returns:
            CategoryResult or None if not found
        """
        manager = CategoryManager(self.db_session)
        category = manager.get_by_id(category_id)
        if category:
            return CategoryResult(category=category)
        return None

    def get_category_by_name(self, name: str) -> CategoryResult | None:
        """
        Get a category by name.

        Args:
            name: Category name

        Returns:
            CategoryResult or None if not found
        """
        manager = CategoryManager(self.db_session)
        category = manager.get_by_name(name)
        if category:
            return CategoryResult(category=category)
        return None

    def list_categories(self) -> list[Category]:
        """
        List all categories.

        Returns:
            List of all categories
        """
        manager = CategoryManager(self.db_session)
        return manager.get_all()

    def update_category(
        self, category_id: int, name: str | None = None, description: str | None = None
    ) -> CategoryResult | None:
        """
        Update a category.

        Args:
            category_id: Category ID
            name: New name (optional)
            description: New description (optional)

        Returns:
            CategoryResult or None if not found
        """
        manager = CategoryManager(self.db_session)

        # Get existing category to build updated version for embedding
        existing_category = manager.get_by_id(category_id)
        if not existing_category:
            return None

        try:
            # Build updated category object for embedding generation
            temp_category = Category(
                name=name if name is not None else existing_category.name,
                description=description
                if description is not None
                else existing_category.description,
            )

            # Regenerate embedding with updated data (idempotent with create)
            embedding = self.embedding_service.embed_category(temp_category)

            category = manager.update(
                category_id, name=name, description=description, embedding=embedding
            )
            if category:
                self.db_session.commit()
                self.db_session.refresh(category)
                return CategoryResult(category=category)
            return None
        except IntegrityError as e:
            self.db_session.rollback()
            raise ValueError(f"Category with name '{name}' already exists") from e
        except Exception:
            self.db_session.rollback()
            raise

    def delete_category(self, category_id: int) -> bool:
        """
        Delete a category.

        Args:
            category_id: Category ID

        Returns:
            True if deleted, False if not found
        """
        manager = CategoryManager(self.db_session)
        try:
            result = manager.delete(category_id)
            if result:
                self.db_session.commit()
            return result
        except Exception:
            self.db_session.rollback()
            raise

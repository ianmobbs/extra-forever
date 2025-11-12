"""
Categories controller for handling API requests.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.deps import get_categories_service
from app.services.categories_service import CategoriesService

logger = logging.getLogger(__name__)


class CategoryRequest(BaseModel):
    """API request model for creating/updating a category."""

    name: str
    description: str


class CategoryUpdateRequest(BaseModel):
    """API request model for updating a category."""

    name: str | None = None
    description: str | None = None


class CategoryResponse(BaseModel):
    """API response model for a category."""

    id: int
    name: str
    description: str


class CategoriesController:
    """Controller for category-related API operations."""

    def __init__(self):
        self.router = APIRouter(prefix="/categories", tags=["categories"])
        self._register_routes()

    def _register_routes(self):
        """Register FastAPI routes."""
        self.router.post("/", response_model=CategoryResponse)(self.create_category)
        self.router.get("/", response_model=list[CategoryResponse])(self.list_categories)
        self.router.get("/{category_id}", response_model=CategoryResponse)(self.get_category)
        self.router.put("/{category_id}", response_model=CategoryResponse)(self.update_category)
        self.router.delete("/{category_id}")(self.delete_category)

    async def create_category(
        self, request: CategoryRequest, service: CategoriesService = Depends(get_categories_service)
    ) -> CategoryResponse:
        """Create a new category."""
        logger.info(f"API: Creating category '{request.name}'")
        try:
            result = service.create_category(request.name, request.description)
            logger.info(f"API: Category '{request.name}' created successfully")
            return CategoryResponse(
                id=result.category.id,
                name=result.category.name,
                description=result.category.description,
            )
        except ValueError as e:
            logger.error(f"API: Failed to create category '{request.name}': {e}")
            raise HTTPException(status_code=400, detail=str(e)) from e

    async def list_categories(
        self, service: CategoriesService = Depends(get_categories_service)
    ) -> list[CategoryResponse]:
        """List all categories."""
        categories = service.list_categories()
        return [
            CategoryResponse(id=cat.id, name=cat.name, description=cat.description)
            for cat in categories
        ]

    async def get_category(
        self, category_id: int, service: CategoriesService = Depends(get_categories_service)
    ) -> CategoryResponse:
        """Get a category by ID."""
        result = service.get_category(category_id)
        if not result:
            raise HTTPException(status_code=404, detail="Category not found")

        return CategoryResponse(
            id=result.category.id,
            name=result.category.name,
            description=result.category.description,
        )

    async def update_category(
        self,
        category_id: int,
        request: CategoryUpdateRequest,
        service: CategoriesService = Depends(get_categories_service),
    ) -> CategoryResponse:
        """Update a category."""
        try:
            result = service.update_category(category_id, request.name, request.description)
            if not result:
                raise HTTPException(status_code=404, detail="Category not found")

            return CategoryResponse(
                id=result.category.id,
                name=result.category.name,
                description=result.category.description,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    async def delete_category(
        self, category_id: int, service: CategoriesService = Depends(get_categories_service)
    ):
        """Delete a category."""
        success = service.delete_category(category_id)
        if not success:
            raise HTTPException(status_code=404, detail="Category not found")

        return {"message": "Category deleted successfully"}

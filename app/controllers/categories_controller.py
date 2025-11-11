"""
Categories controller for handling CLI and API requests.
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.categories_service import CategoriesService
from app.stores.sqlite_store import SQLiteStore


class CategoryRequest(BaseModel):
    """API request model for creating/updating a category."""
    name: str
    description: str


class CategoryUpdateRequest(BaseModel):
    """API request model for updating a category."""
    name: Optional[str] = None
    description: Optional[str] = None


class CategoryResponse(BaseModel):
    """API response model for a category."""
    id: int
    name: str
    description: str


class CategoriesController:
    """Controller for category-related operations."""
    
    def __init__(self, db_path: str = "sqlite:///messages.db"):
        self.store = SQLiteStore(db_path=db_path, echo=False)
        self.store.init_db(drop_existing=False)  # Initialize without dropping
        self.router = APIRouter(prefix="/categories", tags=["categories"])
        self._register_routes()
    
    def _register_routes(self):
        """Register FastAPI routes."""
        self.router.post("/", response_model=CategoryResponse)(self.create_category_api)
        self.router.get("/", response_model=List[CategoryResponse])(self.list_categories_api)
        self.router.get("/{category_id}", response_model=CategoryResponse)(self.get_category_api)
        self.router.put("/{category_id}", response_model=CategoryResponse)(self.update_category_api)
        self.router.delete("/{category_id}")(self.delete_category_api)
    
    async def create_category_api(self, request: CategoryRequest) -> CategoryResponse:
        """
        API endpoint: Create a new category.
        """
        try:
            result = self.create_category(request.name, request.description)
            return CategoryResponse(
                id=result.category.id,
                name=result.category.name,
                description=result.category.description
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    async def list_categories_api(self) -> List[CategoryResponse]:
        """
        API endpoint: List all categories.
        """
        categories = self.list_categories()
        return [
            CategoryResponse(
                id=cat.id,
                name=cat.name,
                description=cat.description
            )
            for cat in categories
        ]
    
    async def get_category_api(self, category_id: int) -> CategoryResponse:
        """
        API endpoint: Get a category by ID.
        """
        result = self.get_category(category_id)
        if not result:
            raise HTTPException(status_code=404, detail="Category not found")
        
        return CategoryResponse(
            id=result.category.id,
            name=result.category.name,
            description=result.category.description
        )
    
    async def update_category_api(
        self,
        category_id: int,
        request: CategoryUpdateRequest
    ) -> CategoryResponse:
        """
        API endpoint: Update a category.
        """
        try:
            result = self.update_category(category_id, request.name, request.description)
            if not result:
                raise HTTPException(status_code=404, detail="Category not found")
            
            return CategoryResponse(
                id=result.category.id,
                name=result.category.name,
                description=result.category.description
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    async def delete_category_api(self, category_id: int):
        """
        API endpoint: Delete a category.
        """
        success = self.delete_category(category_id)
        if not success:
            raise HTTPException(status_code=404, detail="Category not found")
        
        return {"message": "Category deleted successfully"}
    
    # CLI-friendly methods
    
    def create_category(self, name: str, description: str):
        """
        Create a new category.
        
        Args:
            name: Category name
            description: Natural-language description
            
        Returns:
            CategoryResult with the created category
        """
        service = CategoriesService(self.store)
        return service.create_category(name, description)
    
    def get_category(self, category_id: int):
        """
        Get a category by ID.
        
        Args:
            category_id: Category ID
            
        Returns:
            CategoryResult or None
        """
        service = CategoriesService(self.store)
        return service.get_category(category_id)
    
    def get_category_by_name(self, name: str):
        """
        Get a category by name.
        
        Args:
            name: Category name
            
        Returns:
            CategoryResult or None
        """
        service = CategoriesService(self.store)
        return service.get_category_by_name(name)
    
    def list_categories(self):
        """
        List all categories.
        
        Returns:
            List of Category objects
        """
        service = CategoriesService(self.store)
        return service.list_categories()
    
    def update_category(self, category_id: int, name: Optional[str] = None, description: Optional[str] = None):
        """
        Update a category.
        
        Args:
            category_id: Category ID
            name: New name (optional)
            description: New description (optional)
            
        Returns:
            CategoryResult or None
        """
        service = CategoriesService(self.store)
        return service.update_category(category_id, name, description)
    
    def delete_category(self, category_id: int) -> bool:
        """
        Delete a category.
        
        Args:
            category_id: Category ID
            
        Returns:
            True if deleted, False if not found
        """
        service = CategoriesService(self.store)
        return service.delete_category(category_id)


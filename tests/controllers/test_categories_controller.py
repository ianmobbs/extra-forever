"""
Tests for app/controllers/categories_controller.py
"""

import tempfile
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.controllers.categories_controller import CategoriesController


@pytest.fixture
def controller():
    """Create a CategoriesController with temporary database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = f"sqlite:///{tmp.name}"
        controller = CategoriesController(db_path=db_path)
        yield controller
        # Cleanup
        Path(tmp.name).unlink(missing_ok=True)


class TestCategoriesController:
    """Test CategoriesController class."""

    def test_create_category(self, controller):
        """Test creating a category through controller."""
        result = controller.create_category(
            name="Work Travel", description="Work-related travel receipts from airlines"
        )

        assert result.category.id is not None
        assert result.category.name == "Work Travel"
        assert result.category.description == "Work-related travel receipts from airlines"

    def test_get_category(self, controller):
        """Test retrieving a category."""
        created = controller.create_category(name="Test", description="Test category")

        result = controller.get_category(created.category.id)
        assert result is not None
        assert result.category.name == "Test"

    def test_get_category_by_name(self, controller):
        """Test retrieving a category by name."""
        controller.create_category(name="FindMe", description="Test")

        result = controller.get_category_by_name("FindMe")
        assert result is not None
        assert result.category.name == "FindMe"

    def test_list_categories(self, controller):
        """Test listing all categories."""
        controller.create_category(name="Cat1", description="First")
        controller.create_category(name="Cat2", description="Second")
        controller.create_category(name="Cat3", description="Third")

        categories = controller.list_categories()
        assert len(categories) == 3

    def test_update_category(self, controller):
        """Test updating a category."""
        created = controller.create_category(name="OldName", description="Old description")

        result = controller.update_category(
            created.category.id, name="NewName", description="New description"
        )

        assert result is not None
        assert result.category.name == "NewName"
        assert result.category.description == "New description"

    def test_delete_category(self, controller):
        """Test deleting a category."""
        created = controller.create_category(name="ToDelete", description="Will be deleted")

        success = controller.delete_category(created.category.id)
        assert success is True

        # Verify deleted
        result = controller.get_category(created.category.id)
        assert result is None


class TestCategoriesControllerAPI:
    """Test CategoriesController API endpoints."""

    @pytest.fixture
    def client(self):
        """Create a test client with the controller router."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = f"sqlite:///{tmp.name}"
            controller = CategoriesController(db_path=db_path)
            app = FastAPI()
            app.include_router(controller.router)
            client = TestClient(app)
            yield client
            # Cleanup
            Path(tmp.name).unlink(missing_ok=True)

    def test_create_category_api(self, client):
        """Test POST /categories/ endpoint."""
        response = client.post(
            "/categories/", json={"name": "API Test", "description": "Created via API"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "API Test"
        assert data["description"] == "Created via API"
        assert "id" in data

    def test_create_category_api_duplicate(self, client):
        """Test POST /categories/ with duplicate name returns error."""
        # Create first category
        client.post("/categories/", json={"name": "Duplicate", "description": "First"})

        # Try to create duplicate
        response = client.post("/categories/", json={"name": "Duplicate", "description": "Second"})

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    def test_list_categories_api(self, client):
        """Test GET /categories/ endpoint."""
        # Create some categories
        client.post("/categories/", json={"name": "Cat1", "description": "First"})
        client.post("/categories/", json={"name": "Cat2", "description": "Second"})

        response = client.get("/categories/")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] in ["Cat1", "Cat2"]

    def test_get_category_api(self, client):
        """Test GET /categories/{id} endpoint."""
        # Create a category
        create_response = client.post(
            "/categories/", json={"name": "GetMe", "description": "Test get"}
        )
        category_id = create_response.json()["id"]

        # Get the category
        response = client.get(f"/categories/{category_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "GetMe"
        assert data["description"] == "Test get"

    def test_get_category_api_not_found(self, client):
        """Test GET /categories/{id} with non-existent ID."""
        response = client.get("/categories/99999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_update_category_api(self, client):
        """Test PUT /categories/{id} endpoint."""
        # Create a category
        create_response = client.post(
            "/categories/", json={"name": "Original", "description": "Original description"}
        )
        category_id = create_response.json()["id"]

        # Update it
        response = client.put(
            f"/categories/{category_id}",
            json={"name": "Updated", "description": "Updated description"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated"
        assert data["description"] == "Updated description"

    def test_update_category_api_not_found(self, client):
        """Test PUT /categories/{id} with non-existent ID."""
        response = client.put("/categories/99999", json={"name": "Updated"})
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_update_category_api_duplicate_name(self, client):
        """Test PUT /categories/{id} with duplicate name returns error."""
        # Create two categories
        client.post("/categories/", json={"name": "Cat1", "description": "First"})
        response2 = client.post("/categories/", json={"name": "Cat2", "description": "Second"})
        cat2_id = response2.json()["id"]

        # Try to rename Cat2 to Cat1 (duplicate)
        response = client.put(f"/categories/{cat2_id}", json={"name": "Cat1"})

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    def test_delete_category_api(self, client):
        """Test DELETE /categories/{id} endpoint."""
        # Create a category
        create_response = client.post(
            "/categories/", json={"name": "DeleteMe", "description": "Will be deleted"}
        )
        category_id = create_response.json()["id"]

        # Delete it
        response = client.delete(f"/categories/{category_id}")
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"].lower()

        # Verify it's gone
        get_response = client.get(f"/categories/{category_id}")
        assert get_response.status_code == 404

    def test_delete_category_api_not_found(self, client):
        """Test DELETE /categories/{id} with non-existent ID."""
        response = client.delete("/categories/99999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

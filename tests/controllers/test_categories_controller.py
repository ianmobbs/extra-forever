"""
Tests for app/controllers/categories_controller.py and CategoriesService.
"""

import tempfile
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.controllers.categories_controller import CategoriesController
from app.deps import get_categories_service
from app.services.categories_service import CategoriesService
from app.stores.sqlite_store import SQLiteStore


@pytest.fixture
def service():
    """Create a CategoriesService with temporary database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = f"sqlite:///{tmp.name}"
        store = SQLiteStore(db_path=db_path, echo=False)
        store.init_db(drop_existing=True)

        session = store.create_session()
        service = CategoriesService(session)
        yield service

        # Cleanup
        session.close()
        Path(tmp.name).unlink(missing_ok=True)


class TestCategoriesService:
    """Test CategoriesService business logic."""

    def test_create_category(self, service):
        """Test creating a category through service."""
        result = service.create_category(
            name="Work Travel", description="Work-related travel receipts from airlines"
        )

        assert result.category.id is not None
        assert result.category.name == "Work Travel"
        assert result.category.description == "Work-related travel receipts from airlines"

    def test_get_category(self, service):
        """Test retrieving a category."""
        created = service.create_category(name="Test", description="Test category")

        result = service.get_category(created.category.id)
        assert result is not None
        assert result.category.name == "Test"

    def test_get_category_by_name(self, service):
        """Test retrieving a category by name."""
        service.create_category(name="FindMe", description="Test")

        result = service.get_category_by_name("FindMe")
        assert result is not None
        assert result.category.name == "FindMe"

    def test_list_categories(self, service):
        """Test listing all categories."""
        service.create_category(name="Cat1", description="First")
        service.create_category(name="Cat2", description="Second")
        service.create_category(name="Cat3", description="Third")

        categories = service.list_categories()
        assert len(categories) == 3

    def test_update_category(self, service):
        """Test updating a category."""
        created = service.create_category(name="OldName", description="Old description")

        result = service.update_category(
            created.category.id, name="NewName", description="New description"
        )

        assert result is not None
        assert result.category.name == "NewName"
        assert result.category.description == "New description"

    def test_delete_category(self, service):
        """Test deleting a category."""
        created = service.create_category(name="ToDelete", description="Will be deleted")

        success = service.delete_category(created.category.id)
        assert success is True

        # Verify deleted
        result = service.get_category(created.category.id)
        assert result is None


class TestCategoriesControllerAPI:
    """Test CategoriesController API endpoints."""

    @pytest.fixture
    def client(self):
        """Create a test client with dependency overrides."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = f"sqlite:///{tmp.name}"
            store = SQLiteStore(db_path=db_path, echo=False)
            store.init_db(drop_existing=True)

            # Create a session for the test service
            session = store.create_session()
            test_service = CategoriesService(session)

            # Override the dependency
            def override_get_categories_service():
                return test_service

            controller = CategoriesController()
            app = FastAPI()
            app.include_router(controller.router)
            app.dependency_overrides[get_categories_service] = override_get_categories_service

            client = TestClient(app)
            yield client

            # Cleanup
            session.close()
            Path(tmp.name).unlink(missing_ok=True)

    def test_create_category_api(self, client):
        """Test creating a category via API."""
        response = client.post(
            "/categories/",
            json={"name": "API Test", "description": "Created via API"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "API Test"
        assert "id" in data

    def test_create_category_api_duplicate(self, client):
        """Test creating duplicate category fails."""
        client.post(
            "/categories/",
            json={"name": "Duplicate", "description": "First"},
        )
        response = client.post(
            "/categories/",
            json={"name": "Duplicate", "description": "Second"},
        )
        assert response.status_code == 400

    def test_list_categories_api(self, client):
        """Test listing categories via API."""
        client.post("/categories/", json={"name": "Cat1", "description": "First"})
        client.post("/categories/", json={"name": "Cat2", "description": "Second"})

        response = client.get("/categories/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_get_category_api(self, client):
        """Test getting a category via API."""
        create_response = client.post("/categories/", json={"name": "GetMe", "description": "Test"})
        category_id = create_response.json()["id"]

        response = client.get(f"/categories/{category_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "GetMe"

    def test_get_category_api_not_found(self, client):
        """Test getting non-existent category returns 404."""
        response = client.get("/categories/99999")
        assert response.status_code == 404

    def test_update_category_api(self, client):
        """Test updating a category via API."""
        create_response = client.post(
            "/categories/", json={"name": "Old", "description": "Old description"}
        )
        category_id = create_response.json()["id"]

        response = client.put(
            f"/categories/{category_id}",
            json={"name": "New", "description": "New description"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New"
        assert data["description"] == "New description"

    def test_update_category_api_not_found(self, client):
        """Test updating non-existent category returns 404."""
        response = client.put(
            "/categories/99999",
            json={"name": "New", "description": "New"},
        )
        assert response.status_code == 404

    def test_update_category_api_duplicate_name(self, client):
        """Test updating to duplicate name fails."""
        client.post("/categories/", json={"name": "First", "description": "Desc1"})
        create_response = client.post(
            "/categories/", json={"name": "Second", "description": "Desc2"}
        )
        category_id = create_response.json()["id"]

        response = client.put(
            f"/categories/{category_id}",
            json={"name": "First", "description": "Desc2"},
        )
        assert response.status_code == 400

    def test_delete_category_api(self, client):
        """Test deleting a category via API."""
        create_response = client.post(
            "/categories/", json={"name": "DeleteMe", "description": "Test"}
        )
        category_id = create_response.json()["id"]

        response = client.delete(f"/categories/{category_id}")
        assert response.status_code == 200

        # Verify deleted
        get_response = client.get(f"/categories/{category_id}")
        assert get_response.status_code == 404

    def test_delete_category_api_not_found(self, client):
        """Test deleting non-existent category returns 404."""
        response = client.delete("/categories/99999")
        assert response.status_code == 404

    def test_update_category_api_idempotent(self, client):
        """Test that update is idempotent with create (regenerates embeddings)."""
        # Create category
        create_response = client.post(
            "/categories/",
            json={
                "name": "Original Category",
                "description": "Original description for testing idempotency",
            },
        )
        assert create_response.status_code == 200
        category_id = create_response.json()["id"]

        # Update category - should regenerate embedding just like create
        update_response = client.put(
            f"/categories/{category_id}",
            json={
                "name": "Updated Category",
                "description": "Updated description to test embedding regeneration",
            },
        )
        assert update_response.status_code == 200
        updated_data = update_response.json()
        assert updated_data["name"] == "Updated Category"
        assert updated_data["description"] == "Updated description to test embedding regeneration"

        # Verify we can still get the category
        get_response = client.get(f"/categories/{category_id}")
        assert get_response.status_code == 200

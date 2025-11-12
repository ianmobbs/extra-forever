"""
Bootstrap controller for initializing the system with sample data (API only).
"""

import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel

from app.config import config
from app.deps import get_bootstrap_service
from app.services.bootstrap_service import BootstrapService
from app.services.messages_service import ClassificationOptions


class MessagePreview(BaseModel):
    """Preview of a message."""

    id: str
    subject: str
    sender: str


class CategoryPreview(BaseModel):
    """Preview of a category."""

    id: int
    name: str
    description: str


class BootstrapResponse(BaseModel):
    """API response for bootstrap operation."""

    total_categories: int
    total_messages: int
    total_classified: int
    preview_messages: list[MessagePreview]
    preview_categories: list[CategoryPreview]


class BootstrapController:
    """Controller for bootstrap API operations."""

    def __init__(self):
        self.router = APIRouter(prefix="/bootstrap", tags=["bootstrap"])
        self._register_routes()

    def _register_routes(self):
        """Register FastAPI routes."""
        self.router.post("/", response_model=BootstrapResponse)(self.bootstrap_api)

    async def bootstrap_api(
        self,
        messages_file: UploadFile | None = File(None),
        categories_file: UploadFile | None = File(None),
        drop_existing: bool = Form(True),
        auto_classify: bool = Form(False),
        classification_top_n: int = Form(config.CLASSIFICATION_TOP_N),
        classification_threshold: float = Form(config.CLASSIFICATION_THRESHOLD),
        service: BootstrapService = Depends(get_bootstrap_service),
    ) -> BootstrapResponse:
        """Bootstrap the system with messages and categories via API."""
        messages_path = None
        categories_path = None

        try:
            # Save uploaded files temporarily
            if messages_file:
                with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".jsonl") as tmp:
                    content = await messages_file.read()
                    tmp.write(content)
                    messages_path = Path(tmp.name)

            if categories_file:
                with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".jsonl") as tmp:
                    content = await categories_file.read()
                    tmp.write(content)
                    categories_path = Path(tmp.name)

            classification_opts = ClassificationOptions(
                auto_classify=auto_classify,
                top_n=classification_top_n,
                threshold=classification_threshold,
            )

            result = service.bootstrap(
                messages_file=messages_path,
                categories_file=categories_path,
                drop_existing=drop_existing,
                classification_options=classification_opts,
            )

            # Convert to API response
            return BootstrapResponse(
                total_categories=result.total_categories,
                total_messages=result.total_messages,
                total_classified=result.total_classified,
                preview_messages=[
                    MessagePreview(id=msg.id, subject=msg.subject, sender=msg.sender)
                    for msg in result.preview_messages
                ],
                preview_categories=[
                    CategoryPreview(id=cat.id, name=cat.name, description=cat.description)
                    for cat in result.preview_categories
                ],
            )
        finally:
            # Clean up temp files
            if messages_path:
                messages_path.unlink(missing_ok=True)
            if categories_path:
                categories_path.unlink(missing_ok=True)

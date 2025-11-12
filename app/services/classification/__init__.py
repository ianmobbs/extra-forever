"""Classification service and strategies."""

from app.services.classification.classification_service import (
    ClassificationResult,
    ClassificationService,
)
from app.services.classification.strategies import (
    ClassificationStrategy,
    EmbeddingSimilarityStrategy,
)

__all__ = [
    "ClassificationResult",
    "ClassificationService",
    "ClassificationStrategy",
    "EmbeddingSimilarityStrategy",
]

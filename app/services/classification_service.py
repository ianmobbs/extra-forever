"""
Classification service for categorizing messages using cosine similarity.
"""
import numpy as np
from dataclasses import dataclass
from typing import List, Optional

from models import Message, Category
from app.services.messages_service import MessagesService
from app.services.categories_service import CategoriesService
from app.stores.sqlite_store import SQLiteStore


@dataclass
class ClassificationResult:
    """Result of a classification operation."""
    message: Message
    matched_categories: List[Category]
    scores: List[float]  # Cosine similarity scores for each matched category


class ClassificationService:
    """Service for classifying messages into categories using cosine similarity."""
    
    def __init__(self, store: SQLiteStore, top_n: int = 3, threshold: float = 0.5):
        """
        Initialize the classification service.
        
        Args:
            store: SQLite store for database access
            top_n: Maximum number of categories to return
            threshold: Minimum cosine similarity score to include a category (0-1)
        """
        self.store = store
        self.top_n = top_n
        self.threshold = threshold
    
    def classify_message(self, message_id: str) -> ClassificationResult:
        """
        Classify a message into categories using cosine similarity and assign them.
        
        This both classifies the message and persists the category assignments
        in the database.
        
        Args:
            message_id: ID of the message to classify
            
        Returns:
            ClassificationResult with matched categories and scores
            
        Raises:
            ValueError: If message not found or has no embedding
            ValueError: If no categories exist or none have embeddings
        """
        messages_service = MessagesService(self.store)
        categories_service = CategoriesService(self.store)
        
        # Get the message
        message_result = messages_service.get_message(message_id)
        if not message_result:
            raise ValueError(f"Message with ID {message_id} not found")
        
        message = message_result.message
        if not message.embedding:
            raise ValueError(f"Message {message_id} has no embedding")
        
        # Get all categories with embeddings
        all_categories = categories_service.list_categories()
        categories_with_embeddings = [
            cat for cat in all_categories if cat.embedding
        ]
        
        if not categories_with_embeddings:
            raise ValueError("No categories with embeddings found")
        
        # Compute cosine similarities
        matched_categories, scores = self._compute_similarity(
            message, categories_with_embeddings
        )
        
        # Assign the categories to the message
        # Extract category IDs from result
        category_ids = [cat.id for cat in matched_categories]
        
        # We need to use a session to update the relationships
        from app.managers.message_manager import MessageManager
        from app.managers.category_manager import CategoryManager
        
        session = self.store.create_session()
        try:
            message_manager = MessageManager(session)
            category_manager = CategoryManager(session)
            msg = message_manager.get_by_id(message_id)
            
            if msg:
                # Get fresh category objects from this session
                categories = [category_manager.get_by_id(cat_id) for cat_id in category_ids]
                # Clear existing categories and assign new ones
                msg.categories = categories
                session.commit()
        finally:
            session.close()
        
        return ClassificationResult(
            message=message,
            matched_categories=matched_categories,
            scores=scores
        )
    
    def _compute_similarity(
        self, 
        message: Message, 
        categories: List[Category]
    ) -> tuple[List[Category], List[float]]:
        """
        Compute cosine similarity between message and categories.
        
        Args:
            message: Message with embedding
            categories: List of categories with embeddings
            
        Returns:
            Tuple of (matched_categories, scores) sorted by score descending
        """
        # Convert message embedding to numpy array
        message_vec = np.array(message.embedding)
        
        # Build category embedding matrix
        category_vecs = np.array([cat.embedding for cat in categories])
        
        # Compute cosine similarity using matrix multiplication
        # cosine_sim = (A · B) / (||A|| * ||B||)
        # We normalize the vectors first, then dot product
        message_norm = message_vec / np.linalg.norm(message_vec)
        category_norms = category_vecs / np.linalg.norm(category_vecs, axis=1, keepdims=True)
        
        # Compute similarities via matrix multiplication
        similarities = category_norms @ message_norm
        
        # Get indices sorted by similarity (descending)
        sorted_indices = np.argsort(similarities)[::-1]
        
        # Filter by threshold and top_n
        matched_categories = []
        scores = []
        
        for idx in sorted_indices:
            if similarities[idx] >= self.threshold and len(matched_categories) < self.top_n:
                matched_categories.append(categories[idx])
                scores.append(float(similarities[idx]))
        
        return matched_categories, scores


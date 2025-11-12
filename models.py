from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""

    pass


class MessageCategory(Base):
    """
    Association object for message-category relationships with classification metadata.

    This stores additional information about each classification beyond just the relationship,
    including the confidence score, explanation, and timestamp.
    """

    __tablename__ = "message_categories"

    message_id = Column(String, ForeignKey("messages.id", ondelete="CASCADE"), primary_key=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True)
    score = Column(Float, nullable=False)  # Classification confidence score (0-1)
    explanation = Column(Text, nullable=False)  # Human-readable explanation
    classified_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))  # Timestamp

    # Relationships to parent objects
    message = relationship("Message", back_populates="message_categories")
    category = relationship("Category", back_populates="category_messages")


class Message(Base):
    """
    ORM model for a Gmail-style message.
    """

    __tablename__ = "messages"

    id = Column(String, primary_key=True)
    subject = Column(String, nullable=False)
    sender = Column("from", String, nullable=False)  # 'from' is SQL reserved word
    to = Column(JSON, nullable=False)
    snippet = Column(String, nullable=True)
    body = Column(Text, nullable=True)
    date = Column(DateTime, nullable=True)
    embedding = Column(JSON, nullable=True)  # List[float] stored as JSON

    # Relationship to association objects
    message_categories = relationship(
        "MessageCategory", back_populates="message", cascade="all, delete-orphan"
    )

    # Convenience property for accessing categories directly
    @property
    def categories(self) -> list["Category"]:
        """Get list of categories for this message."""
        return [mc.category for mc in self.message_categories]

    def __repr__(self):
        body_preview = ""
        if self.body is not None:
            body_preview = self.body[:100].replace("\n", " ").replace("\r", "") + "..."
        return (
            f"<Message(id={self.id}, subject='{self.subject}', sender='{self.sender}', "
            f"to={self.to}, date='{self.date}', body_preview='{body_preview}')>"
        )


class Category(Base):
    """
    ORM model for a custom email category.
    """

    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(Text, nullable=False)
    embedding = Column(JSON, nullable=True)  # List[float] stored as JSON

    # Relationship to association objects
    category_messages = relationship(
        "MessageCategory", back_populates="category", cascade="all, delete-orphan"
    )

    # Convenience property for accessing messages directly
    @property
    def messages(self) -> list["Message"]:
        """Get list of messages for this category."""
        return [cm.message for cm in self.category_messages]

    def __repr__(self):
        desc_preview = ""
        if self.description is not None:
            desc_preview = self.description[:100].replace("\n", " ").replace("\r", "")
            if len(self.description) > 100:
                desc_preview += "..."
        return f"<Category(id={self.id}, name='{self.name}', description='{desc_preview}')>"

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""

    pass


# Many-to-many association table for messages and categories
message_categories = Table(
    "message_categories",
    Base.metadata,
    Column("message_id", String, ForeignKey("messages.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "category_id", Integer, ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True
    ),
)


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

    # Many-to-many relationship with categories
    categories = relationship("Category", secondary=message_categories, back_populates="messages")

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

    # Many-to-many relationship with messages
    messages = relationship("Message", secondary=message_categories, back_populates="categories")

    def __repr__(self):
        desc_preview = ""
        if self.description is not None:
            desc_preview = self.description[:100].replace("\n", " ").replace("\r", "")
            if len(self.description) > 100:
                desc_preview += "..."
        return f"<Category(id={self.id}, name='{self.name}', description='{desc_preview}')>"

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Text, JSON, DateTime

Base = declarative_base()

class Message(Base):
    """
    ORM model for a Gmail-style message.
    """
    __tablename__ = 'messages'

    id = Column(String, primary_key=True)
    subject = Column(String, nullable=False)
    sender = Column("from", String, nullable=False)  # 'from' is SQL reserved word
    to = Column(JSON, nullable=False)
    snippet = Column(String, nullable=True)
    body = Column(Text, nullable=True) 
    date = Column(DateTime, nullable=True)

    def __repr__(self):
        body_preview = ""
        if self.body is not None:
            body_preview = self.body[:100].replace('\n', ' ').replace('\r', '') + "..."
        return (
            f"<Message(id={self.id}, subject='{self.subject}', sender='{self.sender}', "
            f"to={self.to}, date='{self.date}', body_preview='{body_preview}')>"
        )


class Category(Base):
    """
    ORM model for a custom email category.
    """
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(Text, nullable=False)

    def __repr__(self):
        desc_preview = ""
        if self.description is not None:
            desc_preview = self.description[:100].replace('\n', ' ').replace('\r', '')
            if len(self.description) > 100:
                desc_preview += "..."
        return (
            f"<Category(id={self.id}, name='{self.name}', "
            f"description='{desc_preview}')>"
        )

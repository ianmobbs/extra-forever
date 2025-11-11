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
        return (
            f"<Message(id={self.id}, subject='{self.subject}', sender='{self.sender}', "
            f"to={self.to}, date='{self.date}', body_preview='{self.body[:100].replace('\n', ' ').replace('\r', '')}...'>"
        )

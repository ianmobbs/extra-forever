import json
import base64
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Message

SQLITE_DB_PATH = "sqlite:///messages.db"
MESSAGES_FILE = "sample-messages.jsonl"

def main():
    # Create SQLite database (drop existing tables first)
    engine = create_engine(SQLITE_DB_PATH, echo=False)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    messages = []
    with open(MESSAGES_FILE, 'r') as f:
        for line in f:
            data = json.loads(line)
            body_decoded = base64.b64decode(data['body']).decode('utf-8')
            date_obj = datetime.fromisoformat(data['date'].replace('Z', '+00:00')) # ISO-8601 date string to datetime object
            message = Message(
                id=data['id'],
                subject=data['subject'],
                sender=data['from'],
                to=data['to'], 
                snippet=data['snippet'],
                body=body_decoded,
                date=date_obj
            )
            messages.append(message)

    # Add all messages to database
    session.add_all(messages)
    session.commit()
    
    print(f"Loaded {len(messages)} messages into database\n")
    
    # Query and print first 5 messages
    first_five = session.query(Message).limit(5).all()
    print("First 5 messages:")
    print("-" * 80)
    for msg in first_five:
        print(msg)
    
    session.close()


if __name__ == "__main__":
    main()

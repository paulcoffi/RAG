from sqlalchemy.engine import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

engine = create_engine("sqlite:///rag.db")

SessionLocal = sessionmaker(bind=engine, autoflush = False, autocommit = False)

Base = declarative_base()

def get_db():

    db = SessionLocal()

    try: 
        yield db
    finally:
        db.close()

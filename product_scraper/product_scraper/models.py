# models.py
import os
from sqlalchemy import Column, Integer, String, Text, Float, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class Product(Base):
    """
    Example SQLAlchemy model for storing product data in SQLite.
    """
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    shop = Column(String(100), nullable=True)
    url = Column(String(500), nullable=True)
    product_name = Column(String(500), nullable=True)
    price = Column(String(50), nullable=True)
    brand = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    extras = Column(JSON, nullable=True)  # requires SQLAlchemy>=1.3, or use Text

# Set up the engine and session factory
def db_connect(db_path=None):
    """
    Creates a SQLite DB connection using the provided db_path.
    Returns a SQLAlchemy engine.
    """
    # default to 'sqlite:///products.db' if no path is given
    if not db_path:
        db_path = "sqlite:///products.db"
    return create_engine(db_path)

def create_tables(engine):
    Base.metadata.create_all(engine)

def get_session(db_path=None):
    """
    Creates and returns a SQLAlchemy session.
    """
    engine = db_connect(db_path)
    create_tables(engine)
    Session = sessionmaker(bind=engine)
    return Session()

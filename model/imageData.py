from sqlalchemy import create_engine, Column, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class ImageData(Base):
    __tablename__ = 'images'
    id = Column(String, primary_key=True)
    data = Column(String)

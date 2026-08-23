"""Declarative base for all SQLAlchemy models. Every model in app/models/ inherits from this."""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass

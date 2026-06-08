from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import all ORM models so Alembic autogenerate and Base.metadata see them
from app.models.user import EmailChangeRequest, UserProfile  # noqa: E402, F401

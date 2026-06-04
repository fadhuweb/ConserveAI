import enum
from sqlalchemy import Column, Integer, String, Enum as SAEnum
from src.backend.database import Base


class Role(str, enum.Enum):
    manager = "manager"
    admin   = "admin"


class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    username      = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    park_id       = Column(String, nullable=True)   # null for admin / examiner
    role          = Column(SAEnum(Role), nullable=False, default=Role.manager)
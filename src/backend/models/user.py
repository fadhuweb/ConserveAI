import enum
from sqlalchemy import Column, Integer, String, Boolean, Enum as SAEnum
from src.backend.database import Base


class Role(str, enum.Enum):
    manager = "manager"
    admin   = "admin"


class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    username      = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    park_id       = Column(String, nullable=True)   # null for admin
    role          = Column(SAEnum(Role), nullable=False, default=Role.manager)

    # Profile / contact
    full_name     = Column(String, nullable=True)
    email         = Column(String, nullable=True)
    phone         = Column(String, nullable=True)

    # Set True for admin-provisioned accounts; forces a password change on first login
    # so the long-term password is known only to the manager, not the admin.
    must_change_password = Column(Boolean, nullable=False, default=False)

    # Admins can deactivate an account to block sign-in without deleting its history.
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
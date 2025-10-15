from database import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] =  mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(unique = True)
    email: Mapped[str]
    password: Mapped[str]

    messages = relationship("Message", back_populates = "user", cascade = "all, delete-orphan")


class Message(Base):

    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(primary_key = True)
    user_message: Mapped[str]
    ai_message: Mapped[str]
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    user = relationship("User", back_populates = "messages")
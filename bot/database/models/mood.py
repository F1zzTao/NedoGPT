from __future__ import annotations

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.models.base import Base, created_at, int_pk


class MoodModel(Base):
    __tablename__ = "moods"

    id: Mapped[int_pk]
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))

    name: Mapped[str]
    description: Mapped[str] = mapped_column(default="")
    instructions: Mapped[str]
    is_private: Mapped[bool] = mapped_column(default=False)

    created_at: Mapped[created_at]
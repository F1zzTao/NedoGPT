from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.database.models import MoodModel
from bot.database.models.base import Base, big_int_pk, created_at


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[big_int_pk]
    platform: Mapped[str]

    current_mood_id: Mapped[int] = mapped_column(default=0)
    current_model_id: Mapped[Optional[str]] = mapped_column(default="18")

    persona: Mapped[str] = mapped_column(default="")
    created_moods: Mapped[List["MoodModel"]] = relationship("MoodModel")

    is_owner: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[created_at]

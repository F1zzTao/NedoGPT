# ruff: noqa: TC001, TC003, A003, F821
from __future__ import annotations

from sqlalchemy.orm import Mapped, mapped_column

from bot.database.models.base import Base, big_int_pk, created_at


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[big_int_pk]
    user_id: Mapped[int]
    platform: Mapped[str]
    current_mood_id: Mapped[int] = mapped_column(default=0)

    # TODO: Turn this into a foreign table
    #created_moods_ids: Mapped[str]

    persona: Mapped[str]
    current_model_id: Mapped[int] = mapped_column(default=2)

    is_owner: Mapped[bool] = mapped_column(default=False)

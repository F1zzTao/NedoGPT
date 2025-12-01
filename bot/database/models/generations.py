from __future__ import annotations

from typing import Optional

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.models.base import Base, created_at, int_pk


class GenerationsModel(Base):
    __tablename__ = "generations"

    id: Mapped[int_pk]

    response: Mapped[str]
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    model: Mapped[str]
    mood_id: Mapped[Optional[int]] = mapped_column(ForeignKey("moods.id", ondelete="SET NULL"))
    parent_gen_id: Mapped[Optional[int]] = mapped_column(ForeignKey("generations.id", ondelete="CASCADE"))

    created_at: Mapped[created_at]
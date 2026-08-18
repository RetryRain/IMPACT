from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class DroppedBase(DeclarativeBase):
    pass


class DroppedArticle(DroppedBase):
    __tablename__ = "dropped_articles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True
    )
    url: Mapped[str] = mapped_column(String(2048), unique=True, nullable=False, index=True)
    drop_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    cluster_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    dropped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

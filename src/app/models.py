"""TEMPLATE: ORM model = one table. SQLAlchemy 2.0 typed style (Mapped + mapped_column)."""

from datetime import datetime

from sqlalchemy import String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)  # auto-increment PK
    session_id: Mapped[str] = mapped_column(String(100), index=True)  # index = fast lookups by name
    role: Mapped[str | None] = mapped_column(String(20))  # `| None` -> nullable column
    # Explicit type: SQLAlchemy's default for `float` changed (Float -> Double) between versions,
    # which made `alembic check` report a drift. For real money, prefer Numeric(10, 2) + Decimal.
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())  # DB fills the time

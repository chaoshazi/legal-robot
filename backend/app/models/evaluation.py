import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.user import Base


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    consultation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("consultations.id"), nullable=False, index=True
    )
    trace_id: Mapped[str] = mapped_column(Text, nullable=False)
    score_name: Mapped[str] = mapped_column(Text, nullable=False, default="answer_quality")
    score_value: Mapped[float] = mapped_column(Float, nullable=False)
    data_type: Mapped[str] = mapped_column(Text, nullable=False, default="NUMERIC")
    comment: Mapped[str | None] = mapped_column(Text)
    evaluated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

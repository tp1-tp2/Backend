from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Transcription(Base):
    __tablename__ = "transcriptions"

    transcription_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    audio_id: Mapped[str] = mapped_column(String(36), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    audio_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    audio_duration: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    processing_time: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    device_used: Mapped[str] = mapped_column(String(16), nullable=False, server_default="cpu")
    compute_type: Mapped[str] = mapped_column(String(16), nullable=False, server_default="fp32")

    word_confidences: Mapped[list["WordConfidence"]] = relationship(
        back_populates="transcription",
        cascade="all, delete-orphan",
    )


class WordConfidence(Base):
    __tablename__ = "word_confidences"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    transcription_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("transcriptions.transcription_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    word: Mapped[str] = mapped_column(String(255), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    start_time: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    end_time: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)

    transcription: Mapped["Transcription"] = relationship(back_populates="word_confidences")

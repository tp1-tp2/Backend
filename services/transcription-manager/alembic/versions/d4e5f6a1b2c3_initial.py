"""initial

Revision ID: d4e5f6a1b2c3
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a1b2c3"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- transcriptions ---
    op.create_table(
        "transcriptions",
        sa.Column("transcription_id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("audio_id", sa.String(36), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("audio_filename", sa.String(255), nullable=False),
        sa.Column("audio_duration", sa.Numeric(10, 2), nullable=False),
        sa.Column("processing_time", sa.Numeric(10, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("transcription_id"),
    )
    op.create_index("ix_transcriptions_user_id", "transcriptions", ["user_id"])
    op.create_index("ix_transcriptions_created_at", "transcriptions", ["created_at"])

    # --- word_confidences ---
    op.create_table(
        "word_confidences",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("transcription_id", sa.String(36), nullable=False),
        sa.Column("word", sa.String(255), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False),
        sa.Column("start_time", sa.Numeric(10, 3), nullable=False),
        sa.Column("end_time", sa.Numeric(10, 3), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["transcription_id"],
            ["transcriptions.transcription_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_word_confidences_transcription_id",
        "word_confidences",
        ["transcription_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_word_confidences_transcription_id", "word_confidences")
    op.drop_table("word_confidences")
    op.drop_index("ix_transcriptions_created_at", "transcriptions")
    op.drop_index("ix_transcriptions_user_id", "transcriptions")
    op.drop_table("transcriptions")

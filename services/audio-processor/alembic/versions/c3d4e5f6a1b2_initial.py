"""initial

Revision ID: c3d4e5f6a1b2
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a1b2"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- audio_files ---
    op.create_table(
        "audio_files",
        sa.Column("audio_id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("original_format", sa.String(10), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("duration_seconds", sa.Numeric(10, 2), nullable=False),
        sa.Column("sample_rate", sa.Integer(), nullable=False),
        sa.Column("channels", sa.Integer(), nullable=False),
        sa.Column("bit_rate", sa.Integer(), nullable=False),
        sa.Column("storage_path", sa.String(512), nullable=False),
        sa.Column("processed_path", sa.String(512), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("audio_id"),
    )
    op.create_index("ix_audio_files_user_id", "audio_files", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_audio_files_user_id", "audio_files")
    op.drop_table("audio_files")

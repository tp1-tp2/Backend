"""initial — consolidated schema for the E3 monolithic baseline

Revision ID: 0001
Revises:
Create Date: 2026-09-14 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    account_status_enum = sa.Enum("active", "locked", "disabled", name="account_status_enum")

    # --- users_credentials (from auth-service) ---
    op.create_table(
        "users_credentials",
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("account_status", account_status_enum, nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("user_id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_credentials_email", "users_credentials", ["email"])

    # --- token_blocklist (from auth-service) ---
    op.create_table(
        "token_blocklist",
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("blocked_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("token_hash"),
    )
    op.create_index("ix_token_blocklist_user_id", "token_blocklist", ["user_id"])

    # --- user_profiles (from user-service) ---
    op.create_table(
        "user_profiles",
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("user_id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_user_profiles_email", "user_profiles", ["email"])

    # --- audio_files (from audio-processor) ---
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

    # --- transcriptions (from transcription-manager, + device_used/compute_type) ---
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
        sa.Column("device_used", sa.String(16), nullable=False, server_default="cpu"),
        sa.Column("compute_type", sa.String(16), nullable=False, server_default="fp32"),
        sa.PrimaryKeyConstraint("transcription_id"),
    )
    op.create_index("ix_transcriptions_user_id", "transcriptions", ["user_id"])
    op.create_index("ix_transcriptions_created_at", "transcriptions", ["created_at"])

    # --- word_confidences (from transcription-manager) ---
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
            ["transcription_id"], ["transcriptions.transcription_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_word_confidences_transcription_id", "word_confidences", ["transcription_id"])


def downgrade() -> None:
    op.drop_index("ix_word_confidences_transcription_id", "word_confidences")
    op.drop_table("word_confidences")
    op.drop_index("ix_transcriptions_created_at", "transcriptions")
    op.drop_index("ix_transcriptions_user_id", "transcriptions")
    op.drop_table("transcriptions")
    op.drop_index("ix_audio_files_user_id", "audio_files")
    op.drop_table("audio_files")
    op.drop_index("ix_user_profiles_email", "user_profiles")
    op.drop_table("user_profiles")
    op.drop_index("ix_token_blocklist_user_id", "token_blocklist")
    op.drop_table("token_blocklist")
    op.drop_index("ix_users_credentials_email", "users_credentials")
    op.drop_table("users_credentials")
    sa.Enum(name="account_status_enum").drop(op.get_bind(), checkfirst=True)

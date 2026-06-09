"""initial

Revision ID: b2c3d4e5f6a1
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a1"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- user_profiles ---
    op.create_table(
        "user_profiles",
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(100), nullable=False),
        sa.Column("phone_number", sa.String(20), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("user_id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_user_profiles_email", "user_profiles", ["email"])

    # --- email_change_requests ---
    op.create_table(
        "email_change_requests",
        sa.Column("request_id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("old_email", sa.String(255), nullable=False),
        sa.Column("new_email", sa.String(255), nullable=False),
        sa.Column("old_email_token", sa.String(36), nullable=False),
        sa.Column("new_email_token", sa.String(36), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "old_email_verified", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "new_email_verified", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user_profiles.user_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("request_id"),
    )
    op.create_index(
        "ix_email_change_requests_user_id", "email_change_requests", ["user_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_email_change_requests_user_id", "email_change_requests")
    op.drop_table("email_change_requests")
    op.drop_index("ix_user_profiles_email", "user_profiles")
    op.drop_table("user_profiles")

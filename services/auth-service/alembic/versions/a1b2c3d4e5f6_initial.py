"""initial

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- users_credentials ---
    # sa.Enum with a name auto-creates the PostgreSQL TYPE on first use.
    # Do NOT call enum.create() separately — op.create_table handles it.
    op.create_table(
        "users_credentials",
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column(
            "account_status",
            sa.Enum("active", "locked", "disabled", name="account_status_enum"),
            nullable=False,
            server_default="active",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("user_id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_credentials_email", "users_credentials", ["email"])

    # --- token_blocklist ---
    op.create_table(
        "token_blocklist",
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("blocked_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("token_hash"),
    )
    op.create_index("ix_token_blocklist_user_id", "token_blocklist", ["user_id"])

    # --- password_recovery_tokens ---
    op.create_table(
        "password_recovery_tokens",
        sa.Column("token", sa.String(64), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.PrimaryKeyConstraint("token"),
    )
    op.create_index(
        "ix_password_recovery_tokens_user_id",
        "password_recovery_tokens",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_password_recovery_tokens_user_id", "password_recovery_tokens")
    op.drop_table("password_recovery_tokens")
    op.drop_index("ix_token_blocklist_user_id", "token_blocklist")
    op.drop_table("token_blocklist")
    op.drop_index("ix_users_credentials_email", "users_credentials")
    op.drop_table("users_credentials")
    sa.Enum(name="account_status_enum").drop(op.get_bind(), checkfirst=True)

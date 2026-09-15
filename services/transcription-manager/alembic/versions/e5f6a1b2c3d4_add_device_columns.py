"""add device_used and compute_type columns

Revision ID: e5f6a1b2c3d4
Revises: d4e5f6a1b2c3
Create Date: 2026-09-14 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5f6a1b2c3d4"
down_revision: Union[str, None] = "d4e5f6a1b2c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "transcriptions",
        sa.Column("device_used", sa.String(16), nullable=False, server_default="cpu"),
    )
    op.add_column(
        "transcriptions",
        sa.Column("compute_type", sa.String(16), nullable=False, server_default="fp32"),
    )


def downgrade() -> None:
    op.drop_column("transcriptions", "compute_type")
    op.drop_column("transcriptions", "device_used")

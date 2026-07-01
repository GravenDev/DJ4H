"""Add rngdleguildconfig table

Revision ID: 3752036c90fa
Revises: 3752036c90fa
Create Date: 2026-07-01 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "af8e3b2c1d5f"
down_revision: Union[str, Sequence[str], None] = "3752036c90fa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rngdleguildconfig",
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("leaderboard_channel_id", sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint("guild_id"),
    )


def downgrade() -> None:
    op.drop_table("rngdleguildconfig")

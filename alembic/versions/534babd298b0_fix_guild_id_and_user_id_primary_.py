"""Fix guild_id and user_id primary between them for jd4h

Revision ID: 534babd298b0
Revises: c818d80153fa
Create Date: 2026-09-30 23:29:56.655212

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '534babd298b0'
down_revision: Union[str, Sequence[str], None] = 'c818d80153fa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users_new",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("score", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("user_id", "guild_id"),
    )

    op.execute("""
        INSERT INTO users_new (user_id, guild_id, score)
        SELECT user_id, guild_id, score
        FROM users
    """)

    op.drop_table("users")
    op.rename_table("users_new", "users")


def downgrade() -> None:
    op.create_table(
        "users_old",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("score", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.execute("""
        INSERT INTO users_old (user_id, guild_id, score)
        SELECT user_id, guild_id, score
        FROM users
    """)

    op.drop_table("users")
    op.rename_table("users_old", "users")

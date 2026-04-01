"""create stg_eonet categories

Revision ID: ef7486a70ab4
Revises: bee1d46bf816
Create Date: 2026-04-01 22:28:50.191823

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "ef7486a70ab4"
down_revision: Union[str, Sequence[str], None] = "bee1d46bf816"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True, nullable=False),

        sa.Column("category_id", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("link", sa.Text(), nullable=True),
        sa.Column("layers", postgresql.JSONB(astext_type=sa.Text()), nullable=True),

        sa.Column("s_ingested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("s_source_url", sa.Text(), nullable=False),
        sa.Column("s_run_id", sa.BigInteger(), nullable=False),
        sa.Column("s_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),

        sa.ForeignKeyConstraint(["s_run_id"], ["tech.run_management.s_run_id"], ondelete="CASCADE"),
        sa.UniqueConstraint("category_id", "s_run_id", name="uq_stg_eonet_categories_category_id_run_id"),
        schema="stg_eonet",
    )

    op.create_index(
        "ix_stg_eonet_categories_category_id",
        "categories",
        ["category_id"],
        unique=False,
        schema="stg_eonet",
    )

    op.create_index(
        "ix_stg_eonet_categories_s_run_id",
        "categories",
        ["s_run_id"],
        unique=False,
        schema="stg_eonet",
    )


def downgrade() -> None:
    op.drop_index("ix_stg_eonet_categories_s_run_id", table_name="categories", schema="stg_eonet")
    op.drop_index("ix_stg_eonet_categories_category_id", table_name="categories", schema="stg_eonet")
    op.drop_table("categories", schema="stg_eonet")
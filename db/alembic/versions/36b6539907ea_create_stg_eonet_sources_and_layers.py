"""create stg_eonet sources and layers

Revision ID: 36b6539907ea
Revises: 75cdf7768b5f
Create Date: 2026-04-01 22:38:45.922346

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "36b6539907ea"
down_revision: Union[str, Sequence[str], None] = "75cdf7768b5f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True, nullable=False),

        sa.Column("source_id", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column("link", sa.Text(), nullable=True),

        sa.Column("s_ingested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("s_source_url", sa.Text(), nullable=False),
        sa.Column("s_run_id", sa.BigInteger(), nullable=False),
        sa.Column("s_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),

        sa.ForeignKeyConstraint(["s_run_id"], ["tech.run_management.s_run_id"], ondelete="CASCADE"),
        sa.UniqueConstraint("source_id", "s_run_id", name="uq_stg_eonet_sources_source_id_run_id"),
        schema="stg_eonet",
    )

    op.create_index(
        "ix_stg_eonet_sources_source_id",
        "sources",
        ["source_id"],
        unique=False,
        schema="stg_eonet",
    )

    op.create_index(
        "ix_stg_eonet_sources_s_run_id",
        "sources",
        ["s_run_id"],
        unique=False,
        schema="stg_eonet",
    )

    op.create_table(
        "layers",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True, nullable=False),

        sa.Column("layer_id", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("subtitle", sa.Text(), nullable=True),
        sa.Column("citation", sa.Text(), nullable=True),
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("formats", postgresql.JSONB(astext_type=sa.Text()), nullable=True),

        sa.Column("s_ingested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("s_source_url", sa.Text(), nullable=False),
        sa.Column("s_run_id", sa.BigInteger(), nullable=False),
        sa.Column("s_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),

        sa.ForeignKeyConstraint(["s_run_id"], ["tech.run_management.s_run_id"], ondelete="CASCADE"),
        sa.UniqueConstraint("layer_id", "s_run_id", name="uq_stg_eonet_layers_layer_id_run_id"),
        schema="stg_eonet",
    )

    op.create_index(
        "ix_stg_eonet_layers_layer_id",
        "layers",
        ["layer_id"],
        unique=False,
        schema="stg_eonet",
    )

    op.create_index(
        "ix_stg_eonet_layers_s_run_id",
        "layers",
        ["s_run_id"],
        unique=False,
        schema="stg_eonet",
    )


def downgrade() -> None:
    op.drop_index("ix_stg_eonet_layers_s_run_id", table_name="layers", schema="stg_eonet")
    op.drop_index("ix_stg_eonet_layers_layer_id", table_name="layers", schema="stg_eonet")
    op.drop_table("layers", schema="stg_eonet")

    op.drop_index("ix_stg_eonet_sources_s_run_id", table_name="sources", schema="stg_eonet")
    op.drop_index("ix_stg_eonet_sources_source_id", table_name="sources", schema="stg_eonet")
    op.drop_table("sources", schema="stg_eonet")
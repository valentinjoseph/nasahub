"""recreate stg_eonet layers with correct shape

Revision ID: fb07461adb87
Revises: 36b6539907ea
Create Date: 2026-04-01 22:45:14.632080

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "fb07461adb87"
down_revision: Union[str, Sequence[str], None] = "36b6539907ea"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_stg_eonet_layers_s_run_id", table_name="layers", schema="stg_eonet")
    op.drop_index("ix_stg_eonet_layers_layer_id", table_name="layers", schema="stg_eonet")
    op.drop_table("layers", schema="stg_eonet")

    op.create_table(
        "layers",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True, nullable=False),

        sa.Column("category_id", sa.BigInteger(), nullable=True),
        sa.Column("category_title", sa.Text(), nullable=True),

        sa.Column("layer_name", sa.Text(), nullable=False),
        sa.Column("service_url", sa.Text(), nullable=True),
        sa.Column("service_type_id", sa.Text(), nullable=True),
        sa.Column("parameters", postgresql.JSONB(astext_type=sa.Text()), nullable=True),

        sa.Column("endpoint_link", sa.Text(), nullable=True),
        sa.Column("response_title", sa.Text(), nullable=True),
        sa.Column("response_description", sa.Text(), nullable=True),

        sa.Column("s_ingested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("s_source_url", sa.Text(), nullable=False),
        sa.Column("s_run_id", sa.BigInteger(), nullable=False),
        sa.Column("s_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),

        sa.ForeignKeyConstraint(["s_run_id"], ["tech.run_management.s_run_id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "category_id",
            "layer_name",
            "s_run_id",
            name="uq_stg_eonet_layers_category_layer_run"
        ),
        schema="stg_eonet",
    )

    op.create_index(
        "ix_stg_eonet_layers_category_id",
        "layers",
        ["category_id"],
        unique=False,
        schema="stg_eonet",
    )

    op.create_index(
        "ix_stg_eonet_layers_layer_name",
        "layers",
        ["layer_name"],
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
    op.drop_index("ix_stg_eonet_layers_layer_name", table_name="layers", schema="stg_eonet")
    op.drop_index("ix_stg_eonet_layers_category_id", table_name="layers", schema="stg_eonet")
    op.drop_table("layers", schema="stg_eonet")

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
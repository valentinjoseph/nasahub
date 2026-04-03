"""create neows staging tables

Revision ID: create_stg_neows_tables
Revises: <previous_revision>
Create Date: 2026-04-03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "289640cdad79"
down_revision: Union[str, Sequence[str], None] = "7f5f3f68dc30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "neo_feed",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("neo_reference_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("nasa_jpl_url", sa.Text(), nullable=True),
        sa.Column("absolute_magnitude_h", sa.Double(), nullable=True),
        sa.Column("is_potentially_hazardous_asteroid", sa.Boolean(), nullable=True),
        sa.Column("is_sentry_object", sa.Boolean(), nullable=True),
        sa.Column("close_approach_date", sa.Date(), nullable=False),
        sa.Column("close_approach_datetime", sa.DateTime(timezone=True), nullable=True),
        sa.Column("orbiting_body", sa.Text(), nullable=False),
        sa.Column("estimated_diameter_min_km", sa.Double(), nullable=True),
        sa.Column("estimated_diameter_max_km", sa.Double(), nullable=True),
        sa.Column("relative_velocity_km_per_sec", sa.Double(), nullable=True),
        sa.Column("relative_velocity_km_per_hour", sa.Double(), nullable=True),
        sa.Column("miss_distance_astronomical", sa.Double(), nullable=True),
        sa.Column("miss_distance_lunar", sa.Double(), nullable=True),
        sa.Column("miss_distance_kilometers", sa.Double(), nullable=True),
        sa.Column(
            "s_ingested_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("s_source_url", sa.Text(), nullable=False),
        sa.Column("s_run_id", sa.BigInteger(), nullable=False),
        sa.Column("s_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["s_run_id"], ["tech.run_management.s_run_id"]),
        sa.UniqueConstraint(
            "neo_reference_id",
            "close_approach_date",
            "orbiting_body",
            name="uq_stg_neows_neo_feed",
        ),
        schema="stg_neows",
    )

    op.create_index(
        "ix_stg_neows_neo_feed_run_id",
        "neo_feed",
        ["s_run_id"],
        unique=False,
        schema="stg_neows",
    )
    op.create_index(
        "ix_stg_neows_neo_feed_neo_reference_id",
        "neo_feed",
        ["neo_reference_id"],
        unique=False,
        schema="stg_neows",
    )
    op.create_index(
        "ix_stg_neows_neo_feed_close_approach_date",
        "neo_feed",
        ["close_approach_date"],
        unique=False,
        schema="stg_neows",
    )

    op.create_table(
        "neo_lookup",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("neo_reference_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("nasa_jpl_url", sa.Text(), nullable=True),
        sa.Column("absolute_magnitude_h", sa.Double(), nullable=True),
        sa.Column("is_potentially_hazardous_asteroid", sa.Boolean(), nullable=True),
        sa.Column("is_sentry_object", sa.Boolean(), nullable=True),
        sa.Column("estimated_diameter_min_km", sa.Double(), nullable=True),
        sa.Column("estimated_diameter_max_km", sa.Double(), nullable=True),
        sa.Column(
            "s_ingested_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("s_source_url", sa.Text(), nullable=False),
        sa.Column("s_run_id", sa.BigInteger(), nullable=False),
        sa.Column("s_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["s_run_id"], ["tech.run_management.s_run_id"]),
        sa.UniqueConstraint(
            "neo_reference_id",
            name="uq_stg_neows_neo_lookup",
        ),
        schema="stg_neows",
    )

    op.create_index(
        "ix_stg_neows_neo_lookup_run_id",
        "neo_lookup",
        ["s_run_id"],
        unique=False,
        schema="stg_neows",
    )
    op.create_index(
        "ix_stg_neows_neo_lookup_neo_reference_id",
        "neo_lookup",
        ["neo_reference_id"],
        unique=False,
        schema="stg_neows",
    )

    op.create_table(
        "neo_browse",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("neo_reference_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("nasa_jpl_url", sa.Text(), nullable=True),
        sa.Column("absolute_magnitude_h", sa.Double(), nullable=True),
        sa.Column("is_potentially_hazardous_asteroid", sa.Boolean(), nullable=True),
        sa.Column("is_sentry_object", sa.Boolean(), nullable=True),
        sa.Column("estimated_diameter_min_km", sa.Double(), nullable=True),
        sa.Column("estimated_diameter_max_km", sa.Double(), nullable=True),
        sa.Column(
            "s_ingested_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("s_source_url", sa.Text(), nullable=False),
        sa.Column("s_run_id", sa.BigInteger(), nullable=False),
        sa.Column("s_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["s_run_id"], ["tech.run_management.s_run_id"]),
        sa.UniqueConstraint(
            "neo_reference_id",
            name="uq_stg_neows_neo_browse",
        ),
        schema="stg_neows",
    )

    op.create_index(
        "ix_stg_neows_neo_browse_run_id",
        "neo_browse",
        ["s_run_id"],
        unique=False,
        schema="stg_neows",
    )
    op.create_index(
        "ix_stg_neows_neo_browse_neo_reference_id",
        "neo_browse",
        ["neo_reference_id"],
        unique=False,
        schema="stg_neows",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_stg_neows_neo_browse_neo_reference_id",
        table_name="neo_browse",
        schema="stg_neows",
    )
    op.drop_index(
        "ix_stg_neows_neo_browse_run_id",
        table_name="neo_browse",
        schema="stg_neows",
    )
    op.drop_table("neo_browse", schema="stg_neows")

    op.drop_index(
        "ix_stg_neows_neo_lookup_neo_reference_id",
        table_name="neo_lookup",
        schema="stg_neows",
    )
    op.drop_index(
        "ix_stg_neows_neo_lookup_run_id",
        table_name="neo_lookup",
        schema="stg_neows",
    )
    op.drop_table("neo_lookup", schema="stg_neows")

    op.drop_index(
        "ix_stg_neows_neo_feed_close_approach_date",
        table_name="neo_feed",
        schema="stg_neows",
    )
    op.drop_index(
        "ix_stg_neows_neo_feed_neo_reference_id",
        table_name="neo_feed",
        schema="stg_neows",
    )
    op.drop_index(
        "ix_stg_neows_neo_feed_run_id",
        table_name="neo_feed",
        schema="stg_neows",
    )
    op.drop_table("neo_feed", schema="stg_neows")
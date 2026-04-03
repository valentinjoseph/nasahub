"""add celestrak staging tables

Revision ID: 33021e4cb4c6
Revises: 7f5f3f68dc30
Create Date: 2026-04-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "33021e4cb4c6"
down_revision: Union[str, Sequence[str], None] = "37d227105faa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS stg_celestrak")

    op.create_table(
        "gp_active",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("norad_cat_id", sa.BigInteger(), nullable=False),
        sa.Column("object_name", sa.Text(), nullable=True),
        sa.Column("object_id", sa.Text(), nullable=True),
        sa.Column("epoch", sa.Text(), nullable=True),
        sa.Column("mean_motion", sa.Numeric(), nullable=True),
        sa.Column("eccentricity", sa.Numeric(), nullable=True),
        sa.Column("inclination", sa.Numeric(), nullable=True),
        sa.Column("raan", sa.Numeric(), nullable=True),
        sa.Column("arg_perigee", sa.Numeric(), nullable=True),
        sa.Column("mean_anomaly", sa.Numeric(), nullable=True),
        sa.Column("ephemeris_type", sa.Integer(), nullable=True),
        sa.Column("classification_type", sa.Text(), nullable=True),
        sa.Column("element_set_no", sa.Integer(), nullable=True),
        sa.Column("rev_at_epoch", sa.Integer(), nullable=True),
        sa.Column("bstar", sa.Numeric(), nullable=True),
        sa.Column("mean_motion_dot", sa.Numeric(), nullable=True),
        sa.Column("mean_motion_ddot", sa.Numeric(), nullable=True),
        sa.Column("s_ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("s_source_url", sa.Text(), nullable=False),
        sa.Column("s_run_id", sa.BigInteger(), nullable=False),
        sa.Column("s_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(
            ["s_run_id"],
            ["tech.run_management.s_run_id"],
        ),
        schema="stg_celestrak",
    )
    op.create_unique_constraint(
        "uq_stg_celestrak_gp_active_norad_cat_id",
        "gp_active",
        ["norad_cat_id"],
        schema="stg_celestrak",
    )

    op.create_table(
        "satcat_active",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("norad_cat_id", sa.BigInteger(), nullable=False),
        sa.Column("object_name", sa.Text(), nullable=True),
        sa.Column("object_id", sa.Text(), nullable=True),
        sa.Column("object_type", sa.Text(), nullable=True),
        sa.Column("ops_status_code", sa.Text(), nullable=True),
        sa.Column("owner", sa.Text(), nullable=True),
        sa.Column("launch_date", sa.Text(), nullable=True),
        sa.Column("launch_site", sa.Text(), nullable=True),
        sa.Column("decay_date", sa.Text(), nullable=True),
        sa.Column("period", sa.Numeric(), nullable=True),
        sa.Column("inclination", sa.Numeric(), nullable=True),
        sa.Column("apogee", sa.Numeric(), nullable=True),
        sa.Column("perigee", sa.Numeric(), nullable=True),
        sa.Column("rcs", sa.Numeric(), nullable=True),
        sa.Column("rcs_size", sa.Text(), nullable=True),
        sa.Column("country", sa.Text(), nullable=True),
        sa.Column("s_ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("s_source_url", sa.Text(), nullable=False),
        sa.Column("s_run_id", sa.BigInteger(), nullable=False),
        sa.Column("s_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(
            ["s_run_id"],
            ["tech.run_management.s_run_id"],
        ),
        schema="stg_celestrak",
    )
    op.create_unique_constraint(
        "uq_stg_celestrak_satcat_active_norad_cat_id",
        "satcat_active",
        ["norad_cat_id"],
        schema="stg_celestrak",
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_stg_celestrak_satcat_active_norad_cat_id",
        "satcat_active",
        schema="stg_celestrak",
        type_="unique",
    )
    op.drop_table("satcat_active", schema="stg_celestrak")

    op.drop_constraint(
        "uq_stg_celestrak_gp_active_norad_cat_id",
        "gp_active",
        schema="stg_celestrak",
        type_="unique",
    )
    op.drop_table("gp_active", schema="stg_celestrak")

    op.execute("DROP SCHEMA IF EXISTS stg_celestrak")
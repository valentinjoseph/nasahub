"""osdr creation

Revision ID: 651fd63e4e65
Revises: 83ced9163d69
Create Date: 2026-04-03 19:16:48.325925

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "651fd63e4e65"
down_revision: Union[str, Sequence[str], None] = "83ced9163d69"
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
        sa.Column("epoch", sa.DateTime(timezone=True), nullable=True),
        sa.Column("mean_motion", sa.Double(), nullable=True),
        sa.Column("eccentricity", sa.Double(), nullable=True),
        sa.Column("inclination", sa.Double(), nullable=True),
        sa.Column("raan", sa.Double(), nullable=True),
        sa.Column("arg_of_pericenter", sa.Double(), nullable=True),
        sa.Column("mean_anomaly", sa.Double(), nullable=True),
        sa.Column("ephemeris_type", sa.Integer(), nullable=True),
        sa.Column("classification_type", sa.Text(), nullable=True),
        sa.Column("element_set_no", sa.Integer(), nullable=True),
        sa.Column("rev_at_epoch", sa.Integer(), nullable=True),
        sa.Column("bstar", sa.Double(), nullable=True),
        sa.Column("mean_motion_dot", sa.Double(), nullable=True),
        sa.Column("mean_motion_ddot", sa.Double(), nullable=True),
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
        sa.UniqueConstraint("norad_cat_id", "epoch", name="uq_stg_celestrak_gp_active"),
        schema="stg_celestrak",
    )

    op.create_index(
        "ix_stg_celestrak_gp_active_run_id",
        "gp_active",
        ["s_run_id"],
        unique=False,
        schema="stg_celestrak",
    )
    op.create_index(
        "ix_stg_celestrak_gp_active_norad_cat_id",
        "gp_active",
        ["norad_cat_id"],
        unique=False,
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
        sa.Column("launch_date", sa.Date(), nullable=True),
        sa.Column("launch_site", sa.Text(), nullable=True),
        sa.Column("decay_date", sa.Date(), nullable=True),
        sa.Column("period", sa.Double(), nullable=True),
        sa.Column("inclination", sa.Double(), nullable=True),
        sa.Column("apogee", sa.Double(), nullable=True),
        sa.Column("perigee", sa.Double(), nullable=True),
        sa.Column("rcs", sa.Double(), nullable=True),
        sa.Column("data_status_code", sa.Text(), nullable=True),
        sa.Column("orbit_center", sa.Text(), nullable=True),
        sa.Column("orbit_type", sa.Text(), nullable=True),
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
        sa.UniqueConstraint("norad_cat_id", name="uq_stg_celestrak_satcat_active"),
        schema="stg_celestrak",
    )

    op.create_index(
        "ix_stg_celestrak_satcat_active_run_id",
        "satcat_active",
        ["s_run_id"],
        unique=False,
        schema="stg_celestrak",
    )
    op.create_index(
        "ix_stg_celestrak_satcat_active_norad_cat_id",
        "satcat_active",
        ["norad_cat_id"],
        unique=False,
        schema="stg_celestrak",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_stg_celestrak_satcat_active_norad_cat_id",
        table_name="satcat_active",
        schema="stg_celestrak",
    )
    op.drop_index(
        "ix_stg_celestrak_satcat_active_run_id",
        table_name="satcat_active",
        schema="stg_celestrak",
    )
    op.drop_table("satcat_active", schema="stg_celestrak")

    op.drop_index(
        "ix_stg_celestrak_gp_active_norad_cat_id",
        table_name="gp_active",
        schema="stg_celestrak",
    )
    op.drop_index(
        "ix_stg_celestrak_gp_active_run_id",
        table_name="gp_active",
        schema="stg_celestrak",
    )
    op.drop_table("gp_active", schema="stg_celestrak")
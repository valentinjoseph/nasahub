"""exoplanet creation

Revision ID: 83ced9163d69
Revises: 289640cdad79
Create Date: 2026-04-03 17:28:21.413354

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "83ced9163d69"
down_revision: Union[str, Sequence[str], None] = "289640cdad79"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS stg_exoplanet")

    op.create_table(
        "ps",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("pl_name", sa.Text(), nullable=False),
        sa.Column("hostname", sa.Text(), nullable=True),
        sa.Column("default_flag", sa.Integer(), nullable=True),
        sa.Column("discoverymethod", sa.Text(), nullable=True),
        sa.Column("disc_year", sa.Integer(), nullable=True),
        sa.Column("disc_facility", sa.Text(), nullable=True),
        sa.Column("ra", sa.Double(), nullable=True),
        sa.Column("dec", sa.Double(), nullable=True),
        sa.Column("sy_dist", sa.Double(), nullable=True),
        sa.Column("pl_orbper", sa.Double(), nullable=True),
        sa.Column("pl_rade", sa.Double(), nullable=True),
        sa.Column("pl_bmasse", sa.Double(), nullable=True),
        sa.Column("st_teff", sa.Double(), nullable=True),
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
        sa.UniqueConstraint("pl_name", name="uq_stg_exoplanet_ps"),
        schema="stg_exoplanet",
    )

    op.create_index(
        "ix_stg_exoplanet_ps_run_id",
        "ps",
        ["s_run_id"],
        unique=False,
        schema="stg_exoplanet",
    )
    op.create_index(
        "ix_stg_exoplanet_ps_pl_name",
        "ps",
        ["pl_name"],
        unique=False,
        schema="stg_exoplanet",
    )

    op.create_table(
        "pscomppars",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("pl_name", sa.Text(), nullable=False),
        sa.Column("hostname", sa.Text(), nullable=True),
        sa.Column("discoverymethod", sa.Text(), nullable=True),
        sa.Column("disc_year", sa.Integer(), nullable=True),
        sa.Column("disc_facility", sa.Text(), nullable=True),
        sa.Column("ra", sa.Double(), nullable=True),
        sa.Column("dec", sa.Double(), nullable=True),
        sa.Column("sy_dist", sa.Double(), nullable=True),
        sa.Column("pl_orbper", sa.Double(), nullable=True),
        sa.Column("pl_rade", sa.Double(), nullable=True),
        sa.Column("pl_bmasse", sa.Double(), nullable=True),
        sa.Column("st_teff", sa.Double(), nullable=True),
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
        sa.UniqueConstraint("pl_name", name="uq_stg_exoplanet_pscomppars"),
        schema="stg_exoplanet",
    )

    op.create_index(
        "ix_stg_exoplanet_pscomppars_run_id",
        "pscomppars",
        ["s_run_id"],
        unique=False,
        schema="stg_exoplanet",
    )
    op.create_index(
        "ix_stg_exoplanet_pscomppars_pl_name",
        "pscomppars",
        ["pl_name"],
        unique=False,
        schema="stg_exoplanet",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_stg_exoplanet_pscomppars_pl_name",
        table_name="pscomppars",
        schema="stg_exoplanet",
    )
    op.drop_index(
        "ix_stg_exoplanet_pscomppars_run_id",
        table_name="pscomppars",
        schema="stg_exoplanet",
    )
    op.drop_table("pscomppars", schema="stg_exoplanet")

    op.drop_index(
        "ix_stg_exoplanet_ps_pl_name",
        table_name="ps",
        schema="stg_exoplanet",
    )
    op.drop_index(
        "ix_stg_exoplanet_ps_run_id",
        table_name="ps",
        schema="stg_exoplanet",
    )
    op.drop_table("ps", schema="stg_exoplanet")
"""add exoplanet analytics views

Revision ID: d1e2f3a4b5c6
Revises: c4d5e6f7a8b9
Create Date: 2026-04-10 23:30:00.000000

"""

from typing import Sequence, Union

from alembic import op


revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, Sequence[str], None] = "c4d5e6f7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE VIEW dmt_generic.v_dmt_exoplanet_discovery_yearly_summary AS
        WITH base AS (
            SELECT
                pl_name,
                hostname,
                disc_year,
                sy_dist
            FROM stg_exoplanet.pscomppars
            WHERE disc_year IS NOT NULL
        ),
        yearly AS (
            SELECT
                disc_year,
                COUNT(*) AS planet_count,
                COUNT(DISTINCT hostname) AS distinct_host_count,
                AVG(sy_dist) AS avg_distance_pc
            FROM base
            GROUP BY disc_year
        )
        SELECT
            disc_year,
            planet_count,
            distinct_host_count,
            avg_distance_pc,
            SUM(planet_count) OVER (ORDER BY disc_year) AS cumulative_planet_count
        FROM yearly
        ORDER BY disc_year DESC;
    """)

    op.execute("""
        CREATE OR REPLACE VIEW dmt_generic.v_dmt_exoplanet_discovery_method_summary AS
        SELECT
            COALESCE(discoverymethod, 'Unknown') AS discovery_method,
            COUNT(*) AS planet_count,
            COUNT(DISTINCT hostname) AS distinct_host_count,
            MIN(disc_year) AS first_disc_year,
            MAX(disc_year) AS last_disc_year,
            AVG(sy_dist) AS avg_distance_pc
        FROM stg_exoplanet.pscomppars
        GROUP BY COALESCE(discoverymethod, 'Unknown')
        ORDER BY planet_count DESC, discovery_method;
    """)

    op.execute("""
        CREATE OR REPLACE VIEW dmt_generic.v_dmt_exoplanet_catalog AS
        SELECT
            pl_name,
            hostname,
            COALESCE(discoverymethod, 'Unknown') AS discovery_method,
            disc_year,
            disc_facility,
            sy_dist,
            pl_orbper,
            pl_rade,
            pl_bmasse,
            st_teff,
            s_ingested_at AS last_ingested_at
        FROM stg_exoplanet.pscomppars
        ORDER BY sy_dist NULLS LAST, pl_name;
    """)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS dmt_generic.v_dmt_exoplanet_catalog;")
    op.execute("DROP VIEW IF EXISTS dmt_generic.v_dmt_exoplanet_discovery_method_summary;")
    op.execute("DROP VIEW IF EXISTS dmt_generic.v_dmt_exoplanet_discovery_yearly_summary;")

"""add dmt_generic views

Revision ID: 854e4dbf9562
Revises: 33021e4cb4c6
Create Date: 2026-04-10 21:41:06.857126

"""

from typing import Sequence, Union

from alembic import op


revision: str = "854e4dbf9562"
down_revision: Union[str, Sequence[str], None] = "33021e4cb4c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE SCHEMA IF NOT EXISTS dmt_generic;
    """)

    op.execute("""
        CREATE OR REPLACE VIEW dmt_generic.v_dmt_ingestion_status AS
        SELECT
            source_name,
            source_endpoint,
            run_started_at AS latest_run_started_at,
            run_finished_at AS latest_run_finished_at,
            status AS latest_status,
            records_inserted AS latest_records_inserted,
            created_at
        FROM (
            SELECT
                rm.*,
                ROW_NUMBER() OVER (
                    PARTITION BY rm.source_name, rm.source_endpoint
                    ORDER BY rm.run_started_at DESC NULLS LAST, rm.created_at DESC NULLS LAST
                ) AS rn
            FROM tech.run_management rm
        ) t
        WHERE rn = 1;
    """)

    op.execute("""
        CREATE OR REPLACE VIEW dmt_generic.v_dmt_neows_daily_summary AS
        SELECT
            close_approach_date,
            COUNT(*) AS neo_count,
            COUNT(*) FILTER (WHERE is_potentially_hazardous_asteroid IS TRUE) AS hazardous_count,
            COUNT(DISTINCT neo_reference_id) AS distinct_object_count,
            AVG(relative_velocity_km_per_hour) AS avg_velocity_km_per_hour,
            MIN(miss_distance_kilometers) AS min_miss_distance_kilometers,
            MAX(miss_distance_kilometers) AS max_miss_distance_kilometers,
            MAX(estimated_diameter_max_km) AS biggest_estimated_diameter_max_km
        FROM stg_neows.neo_feed
        GROUP BY close_approach_date
        ORDER BY close_approach_date DESC;
    """)

    op.execute("""
        CREATE OR REPLACE VIEW dmt_generic.v_dmt_neows_kpis AS
        WITH base AS (
            SELECT
                neo_reference_id AS object_id,
                name AS object_name,
                close_approach_date AS recent_approach_date,
                is_potentially_hazardous_asteroid AS is_hazardous_flag,
                estimated_diameter_max_km * 1000.0 AS est_max_diameter_m,
                relative_velocity_km_per_hour AS velocity_kph,
                miss_distance_kilometers AS miss_distance_km
            FROM stg_neows.neo_feed
        ),
        biggest_object AS (
            SELECT
                'biggest_object_meter'::text AS category,
                object_id,
                object_name,
                est_max_diameter_m,
                velocity_kph,
                recent_approach_date,
                is_hazardous_flag,
                miss_distance_km,
                est_max_diameter_m AS value
            FROM base
            WHERE est_max_diameter_m IS NOT NULL
            ORDER BY est_max_diameter_m DESC, recent_approach_date DESC
            LIMIT 1
        ),
        closest_object AS (
            SELECT
                'closest_miss_km'::text AS category,
                object_id,
                object_name,
                est_max_diameter_m,
                velocity_kph,
                recent_approach_date,
                is_hazardous_flag,
                miss_distance_km,
                miss_distance_km AS value
            FROM base
            WHERE miss_distance_km IS NOT NULL
            ORDER BY miss_distance_km ASC, recent_approach_date DESC
            LIMIT 1
        ),
        fastest_object AS (
            SELECT
                'fastest_object_kph'::text AS category,
                object_id,
                object_name,
                est_max_diameter_m,
                velocity_kph,
                recent_approach_date,
                is_hazardous_flag,
                miss_distance_km,
                velocity_kph AS value
            FROM base
            WHERE velocity_kph IS NOT NULL
            ORDER BY velocity_kph DESC, recent_approach_date DESC
            LIMIT 1
        ),
        most_nb_approaches AS (
            SELECT
                'most_nb_approaches'::text AS category,
                object_id,
                object_name,
                MAX(est_max_diameter_m) AS est_max_diameter_m,
                MAX(velocity_kph) AS velocity_kph,
                MAX(recent_approach_date) AS recent_approach_date,
                BOOL_OR(is_hazardous_flag) AS is_hazardous_flag,
                MIN(miss_distance_km) AS miss_distance_km,
                COUNT(*)::double precision AS value
            FROM base
            GROUP BY object_id, object_name
            ORDER BY COUNT(*) DESC, MAX(recent_approach_date) DESC
            LIMIT 1
        ),
        most_recent_approach AS (
            SELECT
                'most_recent_approach'::text AS category,
                object_id,
                object_name,
                est_max_diameter_m,
                velocity_kph,
                recent_approach_date,
                is_hazardous_flag,
                miss_distance_km,
                EXTRACT(EPOCH FROM recent_approach_date::timestamp) AS value
            FROM base
            ORDER BY recent_approach_date DESC, object_id
            LIMIT 1
        ),
        most_recent_dangerous_approach AS (
            SELECT
                'most_recent_dangerous_approach'::text AS category,
                object_id,
                object_name,
                est_max_diameter_m,
                velocity_kph,
                recent_approach_date,
                is_hazardous_flag,
                miss_distance_km,
                EXTRACT(EPOCH FROM recent_approach_date::timestamp) AS value
            FROM base
            WHERE is_hazardous_flag IS TRUE
            ORDER BY recent_approach_date DESC, object_id
            LIMIT 1
        )
        SELECT * FROM biggest_object
        UNION ALL
        SELECT * FROM closest_object
        UNION ALL
        SELECT * FROM fastest_object
        UNION ALL
        SELECT * FROM most_nb_approaches
        UNION ALL
        SELECT * FROM most_recent_approach
        UNION ALL
        SELECT * FROM most_recent_dangerous_approach;
    """)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS dmt_generic.neows_kpis;")
    op.execute("DROP VIEW IF EXISTS dmt_generic.neows_daily_summary;")
    op.execute("DROP VIEW IF EXISTS dmt_generic.ingestion_status;")
    op.execute("DROP SCHEMA IF EXISTS dmt_generic;")
"""add eonet analytics views

Revision ID: c4d5e6f7a8b9
Revises: 854e4dbf9562
Create Date: 2026-04-10 22:20:00.000000

"""

from typing import Sequence, Union

from alembic import op


revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, Sequence[str], None] = "854e4dbf9562"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE VIEW dmt_generic.v_dmt_eonet_category_summary AS
        WITH latest_events AS (
            SELECT
                event_id,
                title,
                closed,
                categories,
                sources,
                geometry,
                s_ingested_at
            FROM (
                SELECT
                    e.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY e.event_id
                        ORDER BY e.s_ingested_at DESC NULLS LAST, e.id DESC
                    ) AS rn
                FROM stg_eonet.events e
            ) ranked
            WHERE rn = 1
        ),
        expanded AS (
            SELECT
                le.event_id,
                le.title,
                le.closed,
                le.s_ingested_at,
                cat.value ->> 'id' AS category_id,
                cat.value ->> 'title' AS category_title,
                jsonb_array_length(COALESCE(le.sources, '[]'::jsonb)) AS source_count,
                (
                    SELECT MAX((geom.value ->> 'date')::timestamptz)
                    FROM jsonb_array_elements(COALESCE(le.geometry, '[]'::jsonb)) AS geom(value)
                ) AS latest_geometry_at
            FROM latest_events le
            CROSS JOIN LATERAL jsonb_array_elements(COALESCE(le.categories, '[]'::jsonb)) AS cat(value)
        )
        SELECT
            category_id,
            MAX(category_title) AS category_title,
            COUNT(DISTINCT event_id) AS total_events,
            COUNT(DISTINCT event_id) FILTER (WHERE closed IS NULL) AS open_events,
            COUNT(DISTINCT event_id) FILTER (WHERE closed IS NOT NULL) AS closed_events,
            SUM(source_count) AS total_sources,
            MAX(latest_geometry_at) AS latest_geometry_at,
            MAX(s_ingested_at) AS last_ingested_at
        FROM expanded
        GROUP BY category_id
        ORDER BY total_events DESC, category_id;
    """)

    op.execute("""
        CREATE OR REPLACE VIEW dmt_generic.v_dmt_eonet_event_overview AS
        WITH latest_events AS (
            SELECT
                event_id,
                title,
                description,
                link,
                closed,
                categories,
                sources,
                geometry,
                s_ingested_at
            FROM (
                SELECT
                    e.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY e.event_id
                        ORDER BY e.s_ingested_at DESC NULLS LAST, e.id DESC
                    ) AS rn
                FROM stg_eonet.events e
            ) ranked
            WHERE rn = 1
        )
        SELECT
            le.event_id,
            le.title,
            le.description,
            le.link,
            CASE
                WHEN le.closed IS NULL THEN 'open'
                ELSE 'closed'
            END AS event_status,
            le.closed AS closed_at,
            COALESCE(jsonb_array_length(le.categories), 0) AS category_count,
            (
                SELECT string_agg(cat.value ->> 'title', ', ' ORDER BY cat.value ->> 'title')
                FROM jsonb_array_elements(COALESCE(le.categories, '[]'::jsonb)) AS cat(value)
            ) AS category_titles,
            COALESCE(jsonb_array_length(le.sources), 0) AS source_count,
            COALESCE(jsonb_array_length(le.geometry), 0) AS geometry_count,
            (
                SELECT MAX((geom.value ->> 'date')::timestamptz)
                FROM jsonb_array_elements(COALESCE(le.geometry, '[]'::jsonb)) AS geom(value)
            ) AS latest_geometry_at,
            le.s_ingested_at AS last_ingested_at
        FROM latest_events le
        ORDER BY latest_geometry_at DESC NULLS LAST, le.event_id;
    """)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS dmt_generic.v_dmt_eonet_event_overview;")
    op.execute("DROP VIEW IF EXISTS dmt_generic.v_dmt_eonet_category_summary;")

import os
import json

import requests
from sqlalchemy import text

from db.session import engine


NASA_API_KEY = os.getenv("NASA_API_KEY")
NEOWS_LOOKUP_URL = "https://api.nasa.gov/neo/rest/v1/neo"


if not NASA_API_KEY:
    raise ValueError("NASA_API_KEY is not set")


def main(asteroid_id: str):
    response = requests.get(
        f"{NEOWS_LOOKUP_URL}/{asteroid_id}",
        params={"api_key": NASA_API_KEY},
        timeout=30,
    )
    response.raise_for_status()
    neo = response.json()

    estimated_diameter_km = neo.get("estimated_diameter", {}).get("kilometers", {})

    with engine.begin() as conn:
        run_id = conn.execute(
            text("""
                INSERT INTO tech.run_management (
                    s_run_id,
                    source_name,
                    source_endpoint,
                    status,
                    run_started_at,
                    records_inserted,
                    created_at
                )
                VALUES (
                    (SELECT COALESCE(MAX(s_run_id), 0) + 1 FROM tech.run_management),
                    'neows',
                    'neo_lookup',
                    'pending',
                    now(),
                    0,
                    now()
                )
                RETURNING s_run_id
            """)
        ).scalar_one()

        staging_row_id = conn.execute(
            text("""
                INSERT INTO stg_neows.neo_lookup (
                    neo_reference_id,
                    name,
                    nasa_jpl_url,
                    absolute_magnitude_h,
                    is_potentially_hazardous_asteroid,
                    is_sentry_object,
                    estimated_diameter_min_km,
                    estimated_diameter_max_km,
                    s_ingested_at,
                    s_source_url,
                    s_run_id,
                    s_payload
                )
                VALUES (
                    :neo_reference_id,
                    :name,
                    :nasa_jpl_url,
                    :absolute_magnitude_h,
                    :is_potentially_hazardous_asteroid,
                    :is_sentry_object,
                    :estimated_diameter_min_km,
                    :estimated_diameter_max_km,
                    now(),
                    :s_source_url,
                    :s_run_id,
                    CAST(:s_payload AS jsonb)
                )
                ON CONFLICT (neo_reference_id) DO NOTHING
                RETURNING id
            """),
            {
                "neo_reference_id": neo.get("neo_reference_id"),
                "name": neo.get("name"),
                "nasa_jpl_url": neo.get("nasa_jpl_url"),
                "absolute_magnitude_h": neo.get("absolute_magnitude_h"),
                "is_potentially_hazardous_asteroid": neo.get("is_potentially_hazardous_asteroid"),
                "is_sentry_object": neo.get("is_sentry_object"),
                "estimated_diameter_min_km": estimated_diameter_km.get("estimated_diameter_min"),
                "estimated_diameter_max_km": estimated_diameter_km.get("estimated_diameter_max"),
                "s_source_url": response.url,
                "s_run_id": run_id,
                "s_payload": json.dumps(neo),
            },
        ).scalar_one_or_none()

        inserted = 0

        if staging_row_id is not None:
            conn.execute(
                text("""
                    INSERT INTO tech.id_management (
                        source_name,
                        source_table,
                        source_record_id,
                        staging_schema,
                        staging_row_id,
                        s_run_id,
                        s_source_url,
                        s_ingested_at
                    )
                    VALUES (
                        :source_name,
                        :source_table,
                        :source_record_id,
                        :staging_schema,
                        :staging_row_id,
                        :s_run_id,
                        :s_source_url,
                        now()
                    )
                """),
                {
                    "source_name": "neows",
                    "source_table": "neo_lookup",
                    "source_record_id": neo.get("neo_reference_id"),
                    "staging_schema": "stg_neows",
                    "staging_row_id": staging_row_id,
                    "s_run_id": run_id,
                    "s_source_url": response.url,
                },
            )
            inserted = 1

        conn.execute(
            text("""
                UPDATE tech.run_management
                SET status = 'success',
                    run_finished_at = now(),
                    records_inserted = :records_inserted
                WHERE s_run_id = :s_run_id
            """),
            {"s_run_id": run_id, "records_inserted": inserted},
        )

    print(f"Run {run_id} inserted {inserted} neo_lookup rows for asteroid_id={asteroid_id}")


if __name__ == "__main__":
    raise SystemExit("Usage: call main('<asteroid_id>') from Python or add CLI parsing.")
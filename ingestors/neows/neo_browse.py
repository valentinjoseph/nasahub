import os
import json
import time

import requests
from sqlalchemy import text

from db.session import engine


NASA_API_KEY = os.getenv("NASA_API_KEY")
NEOWS_BROWSE_URL = "https://api.nasa.gov/neo/rest/v1/neo/browse"

REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_SLEEP_SECONDS = 5
PAGE_SLEEP_SECONDS = 1


if not NASA_API_KEY:
    raise ValueError("NASA_API_KEY is not set")


def fetch_with_retry(url, params=None):
    last_exc = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < MAX_RETRIES:
                print(f"Request failed (attempt {attempt}/{MAX_RETRIES}): {exc}")
                time.sleep(RETRY_SLEEP_SECONDS)

    raise last_exc


def main():
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
                    'neo_browse',
                    'pending',
                    now(),
                    0,
                    now()
                )
                RETURNING s_run_id
            """)
        ).scalar_one()

    inserted = 0
    next_url = NEOWS_BROWSE_URL
    params = {"api_key": NASA_API_KEY}
    page_count = 0

    try:
        while next_url:
            response = fetch_with_retry(next_url, params=params)
            data = response.json()

            near_earth_objects = data.get("near_earth_objects", [])

            with engine.begin() as conn:
                for neo in near_earth_objects:
                    estimated_diameter_km = neo.get("estimated_diameter", {}).get("kilometers", {})

                    staging_row_id = conn.execute(
                        text("""
                            INSERT INTO stg_neows.neo_browse (
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
                            "name": neo.get("name") or neo.get("id") or neo.get("neo_reference_id"),
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

                    if staging_row_id is None:
                        continue

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
                            "source_table": "neo_browse",
                            "source_record_id": neo.get("neo_reference_id"),
                            "staging_schema": "stg_neows",
                            "staging_row_id": staging_row_id,
                            "s_run_id": run_id,
                            "s_source_url": response.url,
                        },
                    )

                    inserted += 1

            page_count += 1
            print(f"Run {run_id}: processed page {page_count}, inserted so far {inserted}")

            next_url = data.get("links", {}).get("next")
            params = None

            if next_url:
                time.sleep(PAGE_SLEEP_SECONDS)

        with engine.begin() as conn:
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

        print(f"Run {run_id} inserted {inserted} neo_browse rows")

    except Exception as exc:
        with engine.begin() as conn:
            conn.execute(
                text("""
                    UPDATE tech.run_management
                    SET status = 'failed',
                        run_finished_at = now(),
                        records_inserted = :records_inserted
                    WHERE s_run_id = :s_run_id
                """),
                {"s_run_id": run_id, "records_inserted": inserted},
            )
        raise exc


if __name__ == "__main__":
    main()
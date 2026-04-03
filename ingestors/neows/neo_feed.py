import os
import json

import requests
from sqlalchemy import text

from db.session import engine


NASA_API_KEY = os.getenv("NASA_API_KEY")
NEOWS_FEED_URL = "https://api.nasa.gov/neo/rest/v1/feed"

if not NASA_API_KEY:
    raise ValueError("NASA_API_KEY is not set")


def main():
    params = {
        "api_key": NASA_API_KEY,
    }

    response = requests.get(NEOWS_FEED_URL, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    near_earth_objects = data.get("near_earth_objects", {})

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
                    'neo_feed',
                    'pending',
                    now(),
                    0,
                    now()
                )
                RETURNING s_run_id
            """)
        ).scalar_one()

        inserted = 0

        for feed_date, neos in near_earth_objects.items():
            for neo in neos:
                close_approach_data = neo.get("close_approach_data", [])

                for approach in close_approach_data:
                    if approach.get("close_approach_date") != feed_date:
                        continue

                    estimated_diameter_km = neo.get("estimated_diameter", {}).get("kilometers", {})
                    relative_velocity = approach.get("relative_velocity", {})
                    miss_distance = approach.get("miss_distance", {})

                    staging_row_id = conn.execute(
                        text("""
                            INSERT INTO stg_neows.neo_feed (
                                neo_reference_id,
                                name,
                                nasa_jpl_url,
                                absolute_magnitude_h,
                                is_potentially_hazardous_asteroid,
                                is_sentry_object,
                                close_approach_date,
                                close_approach_datetime,
                                orbiting_body,
                                estimated_diameter_min_km,
                                estimated_diameter_max_km,
                                relative_velocity_km_per_sec,
                                relative_velocity_km_per_hour,
                                miss_distance_astronomical,
                                miss_distance_lunar,
                                miss_distance_kilometers,
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
                                :close_approach_date,
                                :close_approach_datetime,
                                :orbiting_body,
                                :estimated_diameter_min_km,
                                :estimated_diameter_max_km,
                                :relative_velocity_km_per_sec,
                                :relative_velocity_km_per_hour,
                                :miss_distance_astronomical,
                                :miss_distance_lunar,
                                :miss_distance_kilometers,
                                now(),
                                :s_source_url,
                                :s_run_id,
                                CAST(:s_payload AS jsonb)
                            )
                            ON CONFLICT (
                                neo_reference_id,
                                close_approach_date,
                                orbiting_body
                            ) DO NOTHING
                            RETURNING id
                        """),
                        {
                            "neo_reference_id": neo.get("neo_reference_id"),
                            "name": neo.get("name"),
                            "nasa_jpl_url": neo.get("nasa_jpl_url"),
                            "absolute_magnitude_h": neo.get("absolute_magnitude_h"),
                            "is_potentially_hazardous_asteroid": neo.get("is_potentially_hazardous_asteroid"),
                            "is_sentry_object": neo.get("is_sentry_object"),
                            "close_approach_date": approach.get("close_approach_date"),
                            "close_approach_datetime": approach.get("close_approach_date_full"),
                            "orbiting_body": approach.get("orbiting_body"),
                            "estimated_diameter_min_km": estimated_diameter_km.get("estimated_diameter_min"),
                            "estimated_diameter_max_km": estimated_diameter_km.get("estimated_diameter_max"),
                            "relative_velocity_km_per_sec": relative_velocity.get("kilometers_per_second"),
                            "relative_velocity_km_per_hour": relative_velocity.get("kilometers_per_hour"),
                            "miss_distance_astronomical": miss_distance.get("astronomical"),
                            "miss_distance_lunar": miss_distance.get("lunar"),
                            "miss_distance_kilometers": miss_distance.get("kilometers"),
                            "s_source_url": response.url,
                            "s_run_id": run_id,
                            "s_payload": json.dumps(
                                {
                                    "feed_date": feed_date,
                                    "neo": neo,
                                    "approach": approach,
                                }
                            ),
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
                            "source_table": "neo_feed",
                            "source_record_id": f"{neo.get('neo_reference_id')}|{approach.get('close_approach_date')}|{approach.get('orbiting_body')}",
                            "staging_schema": "stg_neows",
                            "staging_row_id": staging_row_id,
                            "s_run_id": run_id,
                            "s_source_url": response.url,
                        },
                    )

                    inserted += 1

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

    print(f"Run {run_id} inserted {inserted} neo_feed rows")


if __name__ == "__main__":
    main()
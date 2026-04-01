import json
import requests
from sqlalchemy import text

from db.session import engine

EONET_EVENTS_URL = "https://eonet.gsfc.nasa.gov/api/v3/events"


def main():
    response = requests.get(EONET_EVENTS_URL, timeout=30)
    response.raise_for_status()
    data = response.json()
    events = data.get("events", [])

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
                    'eonet',
                    'events',
                    'pending',
                    now(),
                    0,
                    now()
                )
                RETURNING s_run_id
            """)
        ).scalar_one()

        inserted = 0

        for event in events:
            staging_row_id = conn.execute(
                text("""
                    INSERT INTO stg_eonet.events (
                        event_id,
                        title,
                        description,
                        link,
                        closed,
                        categories,
                        sources,
                        geometry,
                        s_ingested_at,
                        s_source_url,
                        s_run_id,
                        s_payload
                    )
                    VALUES (
                        :event_id,
                        :title,
                        :description,
                        :link,
                        :closed,
                        CAST(:categories AS jsonb),
                        CAST(:sources AS jsonb),
                        CAST(:geometry AS jsonb),
                        now(),
                        :s_source_url,
                        :s_run_id,
                        CAST(:s_payload AS jsonb)
                    )
                    ON CONFLICT (event_id) DO NOTHING
                    RETURNING id
                """),
                {
                    "event_id": event.get("id"),
                    "title": event.get("title"),
                    "description": event.get("description"),
                    "link": event.get("link"),
                    "closed": event.get("closed"),
                    "categories": json.dumps(event.get("categories")),
                    "sources": json.dumps(event.get("sources")),
                    "geometry": json.dumps(event.get("geometry")),
                    "s_source_url": EONET_EVENTS_URL,
                    "s_run_id": run_id,
                    "s_payload": json.dumps(event),
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
                    "source_name": "eonet",
                    "source_table": "events",
                    "source_record_id": event.get("id"),
                    "staging_schema": "stg_eonet",
                    "staging_row_id": staging_row_id,
                    "s_run_id": run_id,
                    "s_source_url": EONET_EVENTS_URL,
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

    print(f"Run {run_id} inserted {inserted} events")


if __name__ == "__main__":
    main()
import json
import requests
from sqlalchemy import text

from db.session import engine

EONET_SOURCES_URL = "https://eonet.gsfc.nasa.gov/api/v3/sources"


def main():
    response = requests.get(EONET_SOURCES_URL, timeout=30)
    response.raise_for_status()
    data = response.json()
    sources = data.get("sources", [])

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
                    'sources',
                    'pending',
                    now(),
                    0,
                    now()
                )
                RETURNING s_run_id
            """)
        ).scalar_one()

        inserted = 0

        for source in sources:
            staging_row_id = conn.execute(
                text("""
                    INSERT INTO stg_eonet.sources (
                        source_id,
                        title,
                        source,
                        link,
                        s_ingested_at,
                        s_source_url,
                        s_run_id,
                        s_payload
                    )
                    VALUES (
                        :source_id,
                        :title,
                        :source,
                        :link,
                        now(),
                        :s_source_url,
                        :s_run_id,
                        CAST(:s_payload AS jsonb)
                    )
                    ON CONFLICT (source_id) DO NOTHING
                    RETURNING id
                """),
                {
                    "source_id": source.get("id"),
                    "title": source.get("title"),
                    "source": source.get("source"),
                    "link": source.get("link"),
                    "s_source_url": EONET_SOURCES_URL,
                    "s_run_id": run_id,
                    "s_payload": json.dumps(source),
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
                    "source_table": "sources",
                    "source_record_id": source.get("id"),
                    "staging_schema": "stg_eonet",
                    "staging_row_id": staging_row_id,
                    "s_run_id": run_id,
                    "s_source_url": EONET_SOURCES_URL,
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

    print(f"Run {run_id} inserted {inserted} sources")


if __name__ == "__main__":
    main()
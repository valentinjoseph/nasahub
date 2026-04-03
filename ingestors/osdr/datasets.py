import json
import requests
from sqlalchemy import text

from db.session import engine


OSDR_DATASETS_URL = "https://visualization.osdr.nasa.gov/biodata/api/v2/datasets/"


def main():
    response = requests.get(OSDR_DATASETS_URL, params={"format": "json"}, timeout=60)
    response.raise_for_status()
    data = response.json()

    if isinstance(data, dict):
        datasets = [
            {"dataset_accession": accession, **payload}
            for accession, payload in data.items()
        ]
    else:
        raise ValueError("Unexpected OSDR datasets response shape")

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
                    'osdr',
                    'datasets',
                    'pending',
                    now(),
                    0,
                    now()
                )
                RETURNING s_run_id
            """)
        ).scalar_one()

        inserted = 0

        for row in datasets:
            dataset_accession = row.get("dataset_accession")

            staging_row_id = conn.execute(
                text("""
                    INSERT INTO stg_osdr.datasets (
                        dataset_accession,
                        title,
                        description,
                        data_source,
                        organism,
                        release_date,
                        repository_url,
                        s_ingested_at,
                        s_source_url,
                        s_run_id,
                        s_payload
                    )
                    VALUES (
                        :dataset_accession,
                        :title,
                        :description,
                        :data_source,
                        :organism,
                        :release_date,
                        :repository_url,
                        now(),
                        :s_source_url,
                        :s_run_id,
                        CAST(:s_payload AS jsonb)
                    )
                    ON CONFLICT (dataset_accession) DO NOTHING
                    RETURNING id
                """),
                {
                    "dataset_accession": dataset_accession,
                    "title": row.get("title"),
                    "description": row.get("description"),
                    "data_source": row.get("data_source"),
                    "organism": row.get("organism"),
                    "release_date": row.get("release_date"),
                    "repository_url": row.get("url"),
                    "s_source_url": response.url,
                    "s_run_id": run_id,
                    "s_payload": json.dumps(row),
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
                        'osdr',
                        'datasets',
                        :source_record_id,
                        'stg_osdr',
                        :staging_row_id,
                        :s_run_id,
                        :s_source_url,
                        now()
                    )
                """),
                {
                    "source_record_id": dataset_accession,
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

    print(f"Run {run_id} inserted {inserted} osdr datasets rows")


if __name__ == "__main__":
    main()
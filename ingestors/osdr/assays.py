import json

import requests
from sqlalchemy import text

from db.session import engine


DATASET_URL_TEMPLATE = "https://visualization.osdr.nasa.gov/biodata/api/v2/dataset/{dataset_accession}/assays/"


def main():
    with engine.begin() as conn:
        dataset_ids = conn.execute(
            text("""
                SELECT dataset_accession
                FROM stg_osdr.datasets
                ORDER BY dataset_accession
            """)
        ).scalars().all()

        run_id = conn.execute(
            text("""
                INSERT INTO tech.run_management (
                    s_run_id, source_name, source_endpoint, status,
                    run_started_at, records_inserted, created_at
                )
                VALUES (
                    (SELECT COALESCE(MAX(s_run_id), 0) + 1 FROM tech.run_management),
                    'osdr', 'assays', 'pending', now(), 0, now()
                )
                RETURNING s_run_id
            """)
        ).scalar_one()

        inserted = 0

        for dataset_accession in dataset_ids:
            response = requests.get(
                DATASET_URL_TEMPLATE.format(dataset_accession=dataset_accession),
                params={"format": "json"},
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()

            assays = data.get("assays", {})
            if not assays:
                dataset_obj = data.get(dataset_accession, {})
                if isinstance(dataset_obj, dict):
                    assays = dataset_obj.get("assays", {})

            for assay_accession, assay_payload in assays.items():
                if not isinstance(assay_payload, dict):
                    assay_payload = {"raw_value": assay_payload}

                staging_row_id = conn.execute(
                    text("""
                        INSERT INTO stg_osdr.assays (
                            assay_accession,
                            dataset_accession,
                            assay_type,
                            technology,
                            platform,
                            title,
                            s_ingested_at,
                            s_source_url,
                            s_run_id,
                            s_payload
                        )
                        VALUES (
                            :assay_accession,
                            :dataset_accession,
                            :assay_type,
                            :technology,
                            :platform,
                            :title,
                            now(),
                            :s_source_url,
                            :s_run_id,
                            CAST(:s_payload AS jsonb)
                        )
                        ON CONFLICT (assay_accession) DO NOTHING
                        RETURNING id
                    """),
                    {
                        "assay_accession": assay_accession,
                        "dataset_accession": dataset_accession,
                        "assay_type": assay_payload.get("measurement type") or assay_payload.get("measurement_type") or assay_payload.get("assay_type"),
                        "technology": assay_payload.get("technology type") or assay_payload.get("technology_type") or assay_payload.get("technology"),
                        "platform": assay_payload.get("platform"),
                        "title": assay_payload.get("title") or assay_accession,
                        "s_source_url": response.url,
                        "s_run_id": run_id,
                        "s_payload": json.dumps(assay_payload),
                    },
                ).scalar_one_or_none()

                if staging_row_id is None:
                    continue

                conn.execute(
                    text("""
                        INSERT INTO tech.id_management (
                            source_name, source_table, source_record_id,
                            staging_schema, staging_row_id, s_run_id,
                            s_source_url, s_ingested_at
                        )
                        VALUES (
                            'osdr', 'assays', :source_record_id,
                            'stg_osdr', :staging_row_id, :s_run_id,
                            :s_source_url, now()
                        )
                    """),
                    {
                        "source_record_id": assay_accession,
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

    print(f"Run {run_id} inserted {inserted} osdr assays rows")


if __name__ == "__main__":
    main()
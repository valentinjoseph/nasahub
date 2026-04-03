import json

import requests
from sqlalchemy import text

from db.session import engine


def main():
    with engine.begin() as conn:
        pairs = conn.execute(
            text("""
                SELECT dataset_accession, assay_accession
                FROM stg_osdr.assays
                ORDER BY dataset_accession, assay_accession
            """)
        ).fetchall()

        run_id = conn.execute(
            text("""
                INSERT INTO tech.run_management (
                    s_run_id, source_name, source_endpoint, status,
                    run_started_at, records_inserted, created_at
                )
                VALUES (
                    (SELECT COALESCE(MAX(s_run_id), 0) + 1 FROM tech.run_management),
                    'osdr', 'samples', 'pending', now(), 0, now()
                )
                RETURNING s_run_id
            """)
        ).scalar_one()

        inserted = 0

        for dataset_accession, assay_accession in pairs:
            url = (
                "https://visualization.osdr.nasa.gov/biodata/api/v2/"
                f"dataset/{dataset_accession}/assay/{assay_accession}/samples/"
            )
            response = requests.get(url, params={"format": "json"}, timeout=60)
            response.raise_for_status()
            data = response.json()

            dataset_obj = data.get(dataset_accession, data)
            assays = dataset_obj.get("assays", {})
            assay_obj = assays.get(assay_accession, {})
            if not assay_obj and len(assays) == 1:
                assay_obj = next(iter(assays.values()))

            samples = assay_obj.get("samples", {})

            for sample_key, sample in samples.items():
                if isinstance(sample, str):
                    sample_accession = sample
                    sample_payload = {"raw_value": sample}
                elif isinstance(sample, dict):
                    sample_payload = sample
                    sample_accession = sample.get("accession") or sample.get("id") or sample_key
                else:
                    sample_accession = str(sample_key)
                    sample_payload = {"raw_value": sample}

                staging_row_id = conn.execute(
                    text("""
                        INSERT INTO stg_osdr.samples (
                            sample_accession, dataset_accession, assay_accession,
                            sample_name, organism, tissue, sex, strain,
                            s_ingested_at, s_source_url, s_run_id, s_payload
                        )
                        VALUES (
                            :sample_accession, :dataset_accession, :assay_accession,
                            :sample_name, :organism, :tissue, :sex, :strain,
                            now(), :s_source_url, :s_run_id, CAST(:s_payload AS jsonb)
                        )
                        ON CONFLICT (sample_accession) DO NOTHING
                        RETURNING id
                    """),
                    {
                        "sample_accession": sample_accession,
                        "dataset_accession": dataset_accession,
                        "assay_accession": assay_accession,
                        "sample_name": sample_payload.get("name") or sample_payload.get("sample name") or sample_payload.get("sample_name") or sample_accession,
                        "organism": sample_payload.get("organism"),
                        "tissue": sample_payload.get("tissue"),
                        "sex": sample_payload.get("sex"),
                        "strain": sample_payload.get("strain"),
                        "s_source_url": response.url,
                        "s_run_id": run_id,
                        "s_payload": json.dumps(sample_payload),
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
                            'osdr', 'samples', :source_record_id,
                            'stg_osdr', :staging_row_id, :s_run_id,
                            :s_source_url, now()
                        )
                    """),
                    {
                        "source_record_id": sample_accession,
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

    print(f"Run {run_id} inserted {inserted} osdr samples rows")


if __name__ == "__main__":
    main()
import json

import requests
from sqlalchemy import text

from db.session import engine


def main():
    with engine.begin() as conn:
        rows = conn.execute(
            text("""
                SELECT dataset_accession, assay_accession, sample_accession, s_payload
                FROM stg_osdr.samples
                ORDER BY dataset_accession, assay_accession, sample_accession
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
                    'osdr', 'files', 'pending', now(), 0, now()
                )
                RETURNING s_run_id
            """)
        ).scalar_one()

    inserted = 0

    try:
        for dataset_accession, assay_accession, sample_accession, sample_payload in rows:
            if isinstance(sample_payload, str):
                sample_payload = json.loads(sample_payload)

            sample_rest_url = sample_payload.get("REST_URL")
            if not sample_rest_url or " " in sample_rest_url:
                print(f"Skipping bad sample REST_URL for {sample_accession}: {sample_rest_url}")
                continue

            url = f"{sample_rest_url}file/*/"

            try:
                response = requests.get(url, params={"format": "json"}, timeout=60)
                response.raise_for_status()
            except requests.RequestException as exc:
                print(f"Skipping sample {sample_accession}: {exc}")
                continue

            data = response.json()

            dataset_obj = data.get(dataset_accession, data)
            assays = dataset_obj.get("assays", {})
            assay_obj = assays.get(assay_accession, {})
            if not assay_obj and len(assays) == 1:
                assay_obj = next(iter(assays.values()))

            samples = assay_obj.get("samples", {})
            sample_obj = samples.get(sample_accession, {})
            if not sample_obj and len(samples) == 1:
                sample_obj = next(iter(samples.values()))

            files = sample_obj.get("files", {})

            with engine.begin() as conn:
                for file_key, row in files.items():
                    if isinstance(row, str):
                        file_accession = row
                        file_payload = {"raw_value": row}
                    elif isinstance(row, dict):
                        file_payload = row
                        file_accession = row.get("accession") or row.get("id") or file_key
                    else:
                        file_accession = str(file_key)
                        file_payload = {"raw_value": row}

                    staging_row_id = conn.execute(
                        text("""
                            INSERT INTO stg_osdr.files (
                                file_accession, dataset_accession, assay_accession, sample_accession,
                                file_name, file_type, file_url, md5sum,
                                s_ingested_at, s_source_url, s_run_id, s_payload
                            )
                            VALUES (
                                :file_accession, :dataset_accession, :assay_accession, :sample_accession,
                                :file_name, :file_type, :file_url, :md5sum,
                                now(), :s_source_url, :s_run_id, CAST(:s_payload AS jsonb)
                            )
                            ON CONFLICT (file_accession) DO NOTHING
                            RETURNING id
                        """),
                        {
                            "file_accession": str(file_accession),
                            "dataset_accession": dataset_accession,
                            "assay_accession": assay_accession,
                            "sample_accession": sample_accession,
                            "file_name": file_payload.get("file name") or file_payload.get("file_name") or file_payload.get("filename") or str(file_accession),
                            "file_type": file_payload.get("data type") or file_payload.get("file_type"),
                            "file_url": file_payload.get("URL") or file_payload.get("url"),
                            "md5sum": file_payload.get("md5sum"),
                            "s_source_url": response.url,
                            "s_run_id": run_id,
                            "s_payload": json.dumps(file_payload),
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
                                'osdr', 'files', :source_record_id,
                                'stg_osdr', :staging_row_id, :s_run_id,
                                :s_source_url, now()
                            )
                        """),
                        {
                            "source_record_id": str(file_accession),
                            "staging_row_id": staging_row_id,
                            "s_run_id": run_id,
                            "s_source_url": response.url,
                        },
                    )

                    inserted += 1

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

        print(f"Run {run_id} inserted {inserted} osdr files rows")

    except Exception:
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
        raise


if __name__ == "__main__":
    main()
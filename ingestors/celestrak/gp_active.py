import json
import requests
from sqlalchemy import text

from db.session import engine

CELESTRAK_GP_ACTIVE_URL = "https://celestrak.org/NORAD/elements/gp.php?GROUP=ACTIVE&FORMAT=JSON"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
}


def main():
    response = requests.get(CELESTRAK_GP_ACTIVE_URL, headers=HEADERS, timeout=60)
    response.raise_for_status()
    records = response.json()

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
                    'celestrak',
                    'gp_active',
                    'pending',
                    now(),
                    0,
                    now()
                )
                RETURNING s_run_id
            """)
        ).scalar_one()

        inserted = 0

        for record in records:
            norad_cat_id = record.get("NORAD_CAT_ID")
            if norad_cat_id is None:
                continue

            staging_row_id = conn.execute(
                text("""
                    INSERT INTO stg_celestrak.gp_active (
                        norad_cat_id,
                        object_name,
                        object_id,
                        epoch,
                        mean_motion,
                        eccentricity,
                        inclination,
                        raan,
                        arg_perigee,
                        mean_anomaly,
                        ephemeris_type,
                        classification_type,
                        element_set_no,
                        rev_at_epoch,
                        bstar,
                        mean_motion_dot,
                        mean_motion_ddot,
                        s_ingested_at,
                        s_source_url,
                        s_run_id,
                        s_payload
                    )
                    VALUES (
                        :norad_cat_id,
                        :object_name,
                        :object_id,
                        :epoch,
                        :mean_motion,
                        :eccentricity,
                        :inclination,
                        :raan,
                        :arg_perigee,
                        :mean_anomaly,
                        :ephemeris_type,
                        :classification_type,
                        :element_set_no,
                        :rev_at_epoch,
                        :bstar,
                        :mean_motion_dot,
                        :mean_motion_ddot,
                        now(),
                        :s_source_url,
                        :s_run_id,
                        CAST(:s_payload AS jsonb)
                    )
                    ON CONFLICT (norad_cat_id) DO NOTHING
                    RETURNING id
                """),
                {
                    "norad_cat_id": record.get("NORAD_CAT_ID"),
                    "object_name": record.get("OBJECT_NAME"),
                    "object_id": record.get("OBJECT_ID"),
                    "epoch": record.get("EPOCH"),
                    "mean_motion": record.get("MEAN_MOTION"),
                    "eccentricity": record.get("ECCENTRICITY"),
                    "inclination": record.get("INCLINATION"),
                    "raan": record.get("RA_OF_ASC_NODE"),
                    "arg_perigee": record.get("ARG_OF_PERICENTER"),
                    "mean_anomaly": record.get("MEAN_ANOMALY"),
                    "ephemeris_type": record.get("EPHEMERIS_TYPE"),
                    "classification_type": record.get("CLASSIFICATION_TYPE"),
                    "element_set_no": record.get("ELEMENT_SET_NO"),
                    "rev_at_epoch": record.get("REV_AT_EPOCH"),
                    "bstar": record.get("BSTAR"),
                    "mean_motion_dot": record.get("MEAN_MOTION_DOT"),
                    "mean_motion_ddot": record.get("MEAN_MOTION_DDOT"),
                    "s_source_url": CELESTRAK_GP_ACTIVE_URL,
                    "s_run_id": run_id,
                    "s_payload": json.dumps(record),
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
                    "source_name": "celestrak",
                    "source_table": "gp_active",
                    "source_record_id": str(norad_cat_id),
                    "staging_schema": "stg_celestrak",
                    "staging_row_id": staging_row_id,
                    "s_run_id": run_id,
                    "s_source_url": CELESTRAK_GP_ACTIVE_URL,
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

    print(f"Run {run_id} inserted {inserted} gp_active records")


if __name__ == "__main__":
    main()
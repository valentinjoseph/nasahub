import json
from urllib.parse import quote_plus

import requests
from sqlalchemy import text

from db.session import engine


EXOPLANET_TAP_SYNC_URL = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"

PSCOMPPARS_QUERY = """
SELECT
    pl_name,
    hostname,
    discoverymethod,
    disc_year,
    disc_facility,
    ra,
    dec,
    sy_dist,
    pl_orbper,
    pl_rade,
    pl_bmasse,
    st_teff
FROM pscomppars
"""


def main():
    params = {
        "query": PSCOMPPARS_QUERY,
        "format": "json",
    }

    response = requests.get(EXOPLANET_TAP_SYNC_URL, params=params, timeout=120)
    response.raise_for_status()
    rows = response.json()

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
                    'exoplanet',
                    'pscomppars',
                    'pending',
                    now(),
                    0,
                    now()
                )
                RETURNING s_run_id
            """)
        ).scalar_one()

        inserted = 0
        source_url = (
            f"{EXOPLANET_TAP_SYNC_URL}"
            f"?query={quote_plus(PSCOMPPARS_QUERY)}&format=json"
        )

        for row in rows:
            staging_row_id = conn.execute(
                text("""
                    INSERT INTO stg_exoplanet.pscomppars (
                        pl_name,
                        hostname,
                        discoverymethod,
                        disc_year,
                        disc_facility,
                        ra,
                        dec,
                        sy_dist,
                        pl_orbper,
                        pl_rade,
                        pl_bmasse,
                        st_teff,
                        s_ingested_at,
                        s_source_url,
                        s_run_id,
                        s_payload
                    )
                    VALUES (
                        :pl_name,
                        :hostname,
                        :discoverymethod,
                        :disc_year,
                        :disc_facility,
                        :ra,
                        :dec,
                        :sy_dist,
                        :pl_orbper,
                        :pl_rade,
                        :pl_bmasse,
                        :st_teff,
                        now(),
                        :s_source_url,
                        :s_run_id,
                        CAST(:s_payload AS jsonb)
                    )
                    ON CONFLICT (pl_name) DO NOTHING
                    RETURNING id
                """),
                {
                    "pl_name": row.get("pl_name"),
                    "hostname": row.get("hostname"),
                    "discoverymethod": row.get("discoverymethod"),
                    "disc_year": row.get("disc_year"),
                    "disc_facility": row.get("disc_facility"),
                    "ra": row.get("ra"),
                    "dec": row.get("dec"),
                    "sy_dist": row.get("sy_dist"),
                    "pl_orbper": row.get("pl_orbper"),
                    "pl_rade": row.get("pl_rade"),
                    "pl_bmasse": row.get("pl_bmasse"),
                    "st_teff": row.get("st_teff"),
                    "s_source_url": source_url,
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
                    "source_name": "exoplanet",
                    "source_table": "pscomppars",
                    "source_record_id": row.get("pl_name"),
                    "staging_schema": "stg_exoplanet",
                    "staging_row_id": staging_row_id,
                    "s_run_id": run_id,
                    "s_source_url": source_url,
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

    print(f"Run {run_id} inserted {inserted} exoplanet pscomppars rows")


if __name__ == "__main__":
    main()
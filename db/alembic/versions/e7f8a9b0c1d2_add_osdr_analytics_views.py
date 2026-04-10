"""add osdr analytics views

Revision ID: e7f8a9b0c1d2
Revises: d1e2f3a4b5c6
Create Date: 2026-04-10 23:50:00.000000

"""

from typing import Sequence, Union

from alembic import op


revision: str = "e7f8a9b0c1d2"
down_revision: Union[str, Sequence[str], None] = "d1e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE VIEW dmt_generic.v_dmt_osdr_dataset_summary AS
        WITH assay_counts AS (
            SELECT
                dataset_accession,
                COUNT(*) AS assay_count
            FROM stg_osdr.assays
            GROUP BY dataset_accession
        ),
        sample_counts AS (
            SELECT
                dataset_accession,
                COUNT(*) AS sample_count,
                COUNT(DISTINCT assay_accession) AS assays_with_samples
            FROM stg_osdr.samples
            GROUP BY dataset_accession
        ),
        file_counts AS (
            SELECT
                dataset_accession,
                COUNT(*) AS file_count,
                COUNT(DISTINCT sample_accession) AS samples_with_files
            FROM stg_osdr.files
            GROUP BY dataset_accession
        )
        SELECT
            d.dataset_accession,
            COALESCE(NULLIF(d.title, ''), d.dataset_accession) AS dataset_label,
            NULLIF(d.title, '') AS title,
            NULLIF(d.description, '') AS description,
            NULLIF(d.data_source, '') AS data_source,
            NULLIF(d.organism, '') AS organism,
            d.release_date,
            d.repository_url,
            COALESCE(a.assay_count, 0) AS assay_count,
            COALESCE(s.sample_count, 0) AS sample_count,
            COALESCE(f.file_count, 0) AS file_count,
            d.s_ingested_at AS last_ingested_at
        FROM stg_osdr.datasets d
        LEFT JOIN assay_counts a ON a.dataset_accession = d.dataset_accession
        LEFT JOIN sample_counts s ON s.dataset_accession = d.dataset_accession
        LEFT JOIN file_counts f ON f.dataset_accession = d.dataset_accession
        ORDER BY file_count DESC, sample_count DESC, d.dataset_accession;
    """)

    op.execute("""
        CREATE OR REPLACE VIEW dmt_generic.v_dmt_osdr_assay_type_summary AS
        SELECT
            COALESCE(NULLIF(assay_type, ''), 'Unknown') AS assay_type,
            COUNT(*) AS assay_count,
            COUNT(DISTINCT dataset_accession) AS distinct_dataset_count,
            COUNT(DISTINCT technology) AS distinct_technology_count,
            COUNT(DISTINCT platform) AS distinct_platform_count
        FROM stg_osdr.assays
        GROUP BY COALESCE(NULLIF(assay_type, ''), 'Unknown')
        ORDER BY assay_count DESC, assay_type;
    """)

    op.execute("""
        CREATE OR REPLACE VIEW dmt_generic.v_dmt_osdr_dataset_catalog AS
        SELECT
            dataset_accession,
            COALESCE(NULLIF(title, ''), dataset_accession) AS dataset_label,
            NULLIF(title, '') AS title,
            NULLIF(description, '') AS description,
            NULLIF(data_source, '') AS data_source,
            NULLIF(organism, '') AS organism,
            release_date,
            repository_url,
            s_ingested_at AS last_ingested_at
        FROM stg_osdr.datasets
        ORDER BY dataset_accession;
    """)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS dmt_generic.v_dmt_osdr_dataset_catalog;")
    op.execute("DROP VIEW IF EXISTS dmt_generic.v_dmt_osdr_assay_type_summary;")
    op.execute("DROP VIEW IF EXISTS dmt_generic.v_dmt_osdr_dataset_summary;")
